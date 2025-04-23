import pandas as pd

# from Reader import Reader, ThingMagic, ZebraRFD40, ReadingData
# from Camera import Camera, Optitrack, OAKD
from dataclasses import dataclass, asdict
from Interpolate import reindex_interp
from multiprocessing import Process, Queue, Manager, Event
import signal
from emmanuel_process import IBLocalizationProcessorDiscovery
import ib_loc
import sys
import glob
import os


class System:
    def __init__(self, reader_type):
        pass
        # if reader_type == 'ThingMagic':
        #     self.reader = ThingMagic()
        # elif reader_type == 'ZebraRFD40':
        #     self.reader = ZebraRFD40()
        # if camera_type == 'Optitrack':
        #     self.camera = Optitrack()
        # if camera_type == 'OAKD':
        #     self.camera = OAKD

    def get_tag_df(self, sync=True, replace_bool=False):
        """
        Returns a pandas dataframe that contains tag reading data. Pass true to sync if you want a synchronous reading, and false for an asynchronous reading,
        pass True to replace_bool if you only want the most recent reading of a tag
        """
        if sync:
            tag_data = self.reader.sync_reading()
        else:
            tag_data = self.reader.async_reading(replace_bool)
        tag_df = pd.DataFrame(asdict(tag_data))
        return tag_df

    def get_interpolate_df(self):
        """
        Returns interpolated dataframe, using rf tag dataframe and 6 dof dataframe, saves results to Interpolated.csv
        """
        # return_dict = Manager().dict()
        # event = Event()
        # event.set()
        #
        # def signal_handler(sig, frame):
        #     print('ar we hitting event clear on error runs?')
        #     event.clear()
        #     print('we done?')
        #     self.reader.reader.stop_reading()
        #     # sys.exit(0)
        #
        # signal.signal(signal.SIGINT, signal_handler)
        # rf_process = Process(target=self.get_tag_df, args=(False, False, return_dict, event))
        # cm_process = Process(target=self.get_camera_df, args=(return_dict, event))
        # cm_process.start()
        # rf_process.start()
        # rf_process.join()
        # cm_process.join()
        # print('when does this happen')
        # return_dict['tag_df'].set_index('timestamp').to_csv('readerdata.csv')
        # tag_df, cm_df = return_dict['tag_df'].set_index('timestamp'), return_dict['cm_df'].set_index('timestamp')

        # list_of_files_opt, list_of_files_rf = glob.glob('data/loc_dataset/optitrack_data/*'), glob.glob('data/reader_data/*')
        # latest_file_opt, latest_file_rf = max(list_of_files_opt, key=os.path.getctime), max(list_of_files_rf, key=os.path.getctime)
        # tag_df, cm_df = pd.read_csv(f'{latest_file_rf}').set_index('timestamp'), pd.read_csv(f'{latest_file_opt}/optitrack.csv').set_index('timestamp')
        # tag_df, cm_df = pd.read_csv('data/reader_data/rfdata_20220802123327(comp4).csv').set_index('timestamp'), pd.read_csv(
        #     'data/loc_dataset/optitrack_data/optitrack(comp4).csv').set_index('timestamp')

        # list_of_files_oak, list_of_files_rf = glob.glob('./depthai_blazepose/final_location_data/*'), glob.glob('data/reader_data/*')
        # latest_file_oak, latest_file_rf = max(list_of_files_oak, key=os.path.getctime), max(list_of_files_rf,
        #                                                                                     key=os.path.getctime)
        # tag_df, cm_df = pd.read_csv(f'{latest_file_rf}').set_index('timestamp'), pd.read_csv(
        #     f'{latest_file_oak}').set_index('TIMESTAMP')

        # list_of_files_oak, list_of_files_rf = glob.glob('./data/loc_dataset/videopose/*'), glob.glob(
        #     'data/reader_data/*')
        # latest_file_oak, latest_file_rf = max(list_of_files_oak, key=os.path.getctime), max(list_of_files_rf,
        #                                                                                     key=os.path.getctime)
        # tag_df, cm_df = pd.read_csv(f'{latest_file_rf}').set_index('timestamp'), pd.read_csv(
        #     f'{latest_file_oak}').set_index('TIMESTAMP')

        list_of_files_ar, list_of_files_rf = glob.glob('./data/loc_dataset/ARKit/*'), glob.glob(                        # Choose where you want to pull data from
            'data/reader_data/*')                                                                                       # by commenting in/out the appropriate files
        latest_file_ar, latest_file_rf = max(list_of_files_ar, key=os.path.getctime), max(list_of_files_rf,
                                                                                            key=os.path.getctime)
        tag_df, cm_df = pd.read_csv(f'{latest_file_rf}').set_index('timestamp'), pd.read_csv(
            f'{latest_file_ar}').set_index('timestamp')

        tag_df_index = tag_df.index
        # tag_df, cm_df = tag_df.drop('Unnamed: 0', 1), cm_df.drop('Unnamed: 0', 1) when using OAK !!!!!
        tag_df = tag_df.drop('Unnamed: 0', 1)
        tag_df_index = pd.to_datetime(tag_df_index)
        cm_df.index, tag_df.index = pd.to_datetime(cm_df.index), pd.to_datetime(tag_df.index)                        # Interpolates location data to fit tag timestamps
        print(cm_df)                                                                                                 # using isaac's reindex_interp function
        print(tag_df)
        interpolated_df = reindex_interp(cm_df, tag_df_index, ts_offset=None)
        # interpolated_df.to_csv('testfile.csv')
        interpolated_df = pd.concat([interpolated_df, tag_df], axis=1, join='outer').dropna(axis=0)
        interpolated_df.to_csv('Interpolated.csv')
        return interpolated_df

    def run_demo(self):
        """
        Localizes rf tags and returns results. Uses location/rf data that is pulled in get_interpolate_df() function.
        """
        self.get_interpolate_df()
        print('reached processing')
        processor = IBLocalizationProcessorDiscovery()
        return processor.run_algorithm(area_map=ib_loc.region_map, sku_map=ib_loc.sku_map)

    def run_local_save_tag(self, sync, csv_filename, append=False, replace_bool=False):
        """
        Runs tag reading and saves results to csv
        """
        tag_df = self.get_tag_df()
        if append:
            write_mode = 'a'
        else:
            write_mode = 'w'
        tag_df.to_csv(csv_filename, mode=write_mode, header=(not append), index=False)

#
sys = System('ThingMagic', 'Optitrack')
print(sys.run_demo())
# processor = IBLocalizationProcessorDiscovery()
# print(processor.run_algorithm(area_map=ib_loc.region_map, sku_map=ib_loc.sku_map))
print('fully complete')