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
    def __init__(self, object_epcs):
        self.reader = mercury.Reader("tmr:///dev/cu.usbserial-AQ00WAJ1")
        self.reader.set_region("NA")
        self.reader.set_read_plan([2], "GEN2", read_power=3000)
        self.save_dir = 'localization/output'


        self.num_distance_calculations = 0
        self.sum_distance_calculations = 0

        self.anchor_epcs = object_epcs

        self.anchor_epcs_rssi = {tag: [] for tag in self.anchor_epcs}
        self.anchor_epcs_rssi_num = {tag: 0 for tag in self.anchor_epcs}
        self.anchor_epcs_rssi_avg = {tag: 0 for tag in self.anchor_epcs}

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

    def async_reading(self, replace, num_readings_per_tag=float("inf")):
        """
        Runs asynchronous reading: will continuously read tags until you hit CTRL-C, and saves the results to a csv, and returns a pandas dataframe of the data
        """
        self.anchor_epcs_rssi = {tag: [] for tag in self.anchor_epcs}
        self.anchor_epcs_rssi_num = {tag: 0 for tag in self.anchor_epcs}
        self.anchor_epcs_rssi_avg = {tag: 0 for tag in self.anchor_epcs}

        def read_update(tag, tag_data, replace_bool):
            tag_data_list = [tag_data.EPC, tag_data.RSSI_VALUE, tag_data.PHASE,
                             tag_data.timestamp]
            if replace_bool:
                if tag.epc.decode("utf-8") in tag_data.EPC:
                    ix = tag_data.EPC.index(tag.epc.decode("utf-8"))
                    for tag_val in tag_data_list:
                        tag_val.pop(ix)
            
            epc_name = tag.epc.decode("utf-8")
            #update anchor tag rssi values with average value 
            if epc_name in self.anchor_epcs_rssi:
                # print(tag.epc.decode("utf-8"))
                if len(self.anchor_epcs_rssi[epc_name]) == 0:
                    self.anchor_epcs_rssi_avg[epc_name] = tag.rssi
                    self.anchor_epcs_rssi[epc_name] = [tag.rssi]
                else:
                    self.anchor_epcs_rssi[epc_name].append(tag.rssi)
                    rssi_sum = sum(self.anchor_epcs_rssi[epc_name])
                    rssi_num = len(self.anchor_epcs_rssi[epc_name])
                    self.anchor_epcs_rssi_avg[epc_name] = rssi_sum / rssi_num
                
                self.anchor_epcs_rssi_num[epc_name] = len(self.anchor_epcs_rssi[epc_name])            
            elif epc_name ==  
            for tag_val, val in zip(tag_data_list, [tag.epc.decode("utf-8"), tag.rssi, tag.phase,
                                                    datetime.fromtimestamp(tag.timestamp).astimezone(
                                                            timezone.utc)]):
                tag_val.append(val)

        tag_data = ReadingData([], [], [], [])
        self.reader.start_reading(lambda tag: read_update(tag, tag_data, False))

        try:
            while min(self.anchor_epcs_rssi_num.values()) < num_readings_per_tag:
                self.localize_reader()
                sleep(1)
        except KeyboardInterrupt:
            self.reader.stop_reading()
            print('Done :)')
            pass
        return tag_data

    def distance(self, rssi):
        d = 10**((-60-(rssi))/(10*3.0))
        return d
    
    def localize_reader(self):

        # fixed positions 
        # anchor_positions = np.array([
        #     [0.0, 0.0, 0.0], # Anchor 1
        #     [2.0, 0.0, 0.0], # Anchor 2
        #     [1.0, 2.0, 1.0]  # Anchor 3
        # ])

        anchor_positions = np.array([
            [0.0], # Anchor 1
            # [0.0, 20.0], # Anchor 2
            # [5.0, 20.0], # Anchor 3
            # [5.0, 0.0], # Anchor 4
        ])

        for anchor in self.anchor_epcs_rssi:
            if self.anchor_epcs_rssi[anchor] == []:
                print(self.anchor_epcs_rssi)
                print("Cannot Localize Reader: Anchors Not Found")
                return

            print(f"Anchor {anchor} AVG RSSI: {self.anchor_epcs_rssi_avg[anchor]}")
            print(f"Anchor {anchor} RSSI: {self.anchor_epcs_rssi[anchor]}")

        distances = np.array([
            self.distance(rssi) for rssi in self.anchor_epcs_rssi_avg.values()
        ])

        def objective(reader_pos):
            return np.sum((np.linalg.norm(reader_pos - anchor_positions, axis=1) - distances)**2)

        initial_guess  = np.mean(anchor_positions, axis=0)
        result = minimize(objective, initial_guess, method='L-BFGS-B')

        if result.success:
            estimated_position = result.x
            self.num_distance_calculations += 1
            self.sum_distance_calculations += estimated_position[0]

            average_position = self.sum_distance_calculations 
            average_position /= self.num_distance_calculations

            print(f"Estimated reader position: {estimated_position}")
            print(f"Estimated average reader position: {average_position}")
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