import mercury
from datetime import datetime, timezone
from time import sleep
from dataclasses import dataclass, asdict

import sys 
print(sys.executable)

import pandas as pd
import numpy as np
from scipy.optimize import minimize 
@dataclass
class ReadingData:
    EPC: list
    RSSI_VALUE: list
    PHASE: list
    timestamp: list


class Reader:
    def __init__(self):
        NotImplemented

    def sync_reading(self):
        NotImplemented

    def async_reading(self):
        NotImplemented


class ThingMagic(Reader):
    def __init__(self):
        self.reader = mercury.Reader("tmr:///dev/cu.usbserial-AQ00WAJ1")
        self.reader.set_region("NA")
        self.reader.set_read_plan([1], "GEN2", read_power=3000)
        self.save_dir = '/home/eant/splitRF/data/reader_data'
        self.anchor_tags_rssi = {
            "D4C3204700000000000000C4": None,
            "E135204700000000000000CA": None,
            "E23456780000000000000031": None
        }

    def sync_reading(self):
        tag_list = self.reader.read()
        epc_list, rssi_list, phase_list, timestamp_list = [tag.epc.decode("utf-8") for tag in tag_list], [tag.rssi for
                                                                                                          tag in
                                                                                                          tag_list], [
                                                              tag.phase for tag in tag_list], [
                                                              datetime.fromtimestamp(tag.timestamp).astimezone(
                                                                  timezone.utc).isoformat() for tag in tag_list]
        tag_data = ReadingData(epc_list, rssi_list, phase_list, timestamp_list)
        return tag_data

    def async_reading(self, replace):
        """
        Runs asynchronous reading: will continuously read tags until you hit CTRL-C, and saves the results to a csv, and returns a pandas dataframe of the data
        """
        def read_update(tag, tag_data, replace_bool):
            tag_data_list = [tag_data.EPC, tag_data.RSSI_VALUE, tag_data.PHASE,
                             tag_data.timestamp]
            if replace_bool:
                if tag.epc.decode("utf-8") in tag_data.EPC:
                    ix = tag_data.EPC.index(tag.epc.decode("utf-8"))
                    for tag_val in tag_data_list:
                        tag_val.pop(ix)
            
            #update anchor tag rssi values
            if tag.epc.decode("utf-8") in self.anchor_tags_rssi:
                # print(tag.epc.decode("utf-8"))
                self.anchor_tags_rssi[tag.epc.decode("utf-8")] = tag.rssi
            
            for tag_val, val in zip(tag_data_list, [tag.epc.decode("utf-8"), tag.rssi, tag.phase,
                                                    datetime.fromtimestamp(tag.timestamp).astimezone(
                                                            timezone.utc)]):
                tag_val.append(val)

        tag_data = ReadingData([], [], [], [])
        self.reader.start_reading(lambda tag: read_update(tag, tag_data, replace))
        try:
            while True:
                self.localize_reader()
                sleep(1)
        except KeyboardInterrupt:
            self.reader.stop_reading()
            print('Done :)')
            pass
        return tag_data

    def distance(self, rssi):
        d = 10**((-72-(rssi))/(10*2.5))
        return d
    
    
    def localize_reader(self):

        # fixed positions 
        anchor_positions = np.array([
            [0.0, 0.0, 0.0], # Anchor 1
            [2.0, 0.0, 0.0], # Anchor 2
            [1.0, 2.0, 1.0]  # Anchor 3
        ])

        for anchor in self.anchor_tags_rssi:
            if self.anchor_tags_rssi[anchor] == None:
                print(self.anchor_tags_rssi)
                print("Cannot Localize Reader: Anchors Not Found")
                return

        distances = np.array([
            self.distance(self.anchor_tags_rssi["D4C3204700000000000000C4"]),
            self.distance(self.anchor_tags_rssi["E135204700000000000000CA"]),
            self.distance(self.anchor_tags_rssi["E23456780000000000000031"])
        ])

        def objective(reader_pos):
            return np.sum((np.linalg.norm(reader_pos - anchor_positions, axis=1) - distances)**2)

        initial_guess  = np.mean(anchor_positions, axis=0)
        result = minimize(objective, initial_guess, method='L-BFGS-B')

        if result.success:
            estimated_position = result.x
            print(f"Estimated reader position: {estimated_position}")
        else:
            print("Optimization failed:", result.message)


if __name__ == "__main__":
    reader = ThingMagic()
    # reader.localize_reader()
    tag_data = reader.async_reading(False)
    tag_df = pd.DataFrame(asdict(tag_data))
    now_strtime = datetime.now().strftime('%Y%m%d%H%M%S')
    print(tag_df)
    tag_df.to_csv(f'{reader.save_dir}/rfdata_{now_strtime}.csv')
    # print(reader.sync_reading())