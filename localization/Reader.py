import mercury
from datetime import datetime, timezone
from time import sleep
from dataclasses import dataclass, asdict
import pandas as pd



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
        self.reader = mercury.Reader("tmr://COM5")
        self.reader.set_region("NA")
        self.reader.set_read_plan([1], "GEN2", read_power=3000)
        self.save_dir = '/c/Users/eante/Downloads/cplates_data/reader_data'


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
            for tag_val, val in zip(tag_data_list, [tag.epc.decode("utf-8"), tag.rssi, tag.phase,
                                                    datetime.fromtimestamp(tag.timestamp).astimezone(
                                                            timezone.utc)]):
                tag_val.append(val)

        tag_data = ReadingData([], [], [], [])
        self.reader.start_reading(lambda tag: read_update(tag, tag_data, replace))
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            self.reader.stop_reading()
            print('Done :)')
            pass
        return tag_data


if __name__ == "__main__":
    reader = ThingMagic()
    tag_data = reader.async_reading(False)
    tag_df = pd.DataFrame(asdict(tag_data))
    now_strtime = datetime.now().strftime('%Y%m%d%H%M%S')
    print(tag_df)
    tag_df.to_csv(f'{reader.save_dir}/rfdata_{now_strtime}.csv')
    # print(reader.sync_reading())