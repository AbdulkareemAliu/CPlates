#This code will need to replace IB localization class in system.py, should localize tags based on 
#signal strength to reader. also need to figure out how to find where reader is based on anchor tags

import mercury
import numpy as np
from scipy.optimize import minimize
from datetime import datetime, timezone
from time import sleep

class RssiLocalizationBase:
    def __init__(self):
        self.zones = {
                        "E135204700000000000000CA": 0,
                        "E23456780000000000000023": 1,
                        "E23456780000000000000031": 2
                      }
        self.zone_count = len(self.zones)
        
        #Maps each zone to the possible distances to every other zone
        #e.g. for zone 0, distances found of 0 to 5 could correspond to zone 1
        self.zone_distance_map = {
            0: {
                0: (0, 5.5),
                1: (0, 11)
            },
            1: {
                0: (0, 5.5),
                1: (0, 11)
            }
        }

        # Maps each zone to their 2d location (x, y)
        self.zone_positions = {
            0: [0, 0],
            1: [6.5, 4],
            2: [12, 0.4],
        }

        self.zone_fingerprints = {
            0: np.array([-50, -60, -70]),
            1: np.array([-60, -50, -90]),
            2: np.array([-70, -90, -50])
        }
        
        self.reader = mercury.Reader("tmr:///dev/cu.usbserial-AQ00WAJ1")
        self.reader.set_region("NA")
        self.reader.set_read_plan([1], "GEN2", read_power=3000)

    def localize_reader(self, tag_count):
        """
        Runs asynchronous reading: will continuously read tags until you hit CTRL-C, and saves the results to a csv, and returns a pandas dataframe of the data
        """
        tag_rssi = {zone_tag: [] for zone_tag in self.zones}

        def read_update(tag):
            epc, rssi = tag.epc.decode("utf-8"), tag.rssi

            if epc in self.zones:
                tag_rssi[epc].append(rssi)
        
        self.reader.start_reading(lambda tag: read_update(tag))
        while min([len(vals) for vals in tag_rssi.values()]) < tag_count:
            sleep(1)

        self.reader.stop_reading()
        #Find zone
        tag_rssi_avg = {zone_tag: 0 for zone_tag in self.zones}
        for zone_tag in self.zones:
            if (len(tag_rssi[zone_tag]) > 0):
                tag_rssi_avg[zone_tag] /= sum(tag_rssi[zone_tag]) / len(tag_rssi[zone_tag])
        
        
        max_rssi_tag = max(self.zones, key=lambda z: max(tag_rssi[z]))
        zone = self.zones[max_rssi_tag]
        return zone, tag_rssi
    
    def distance(self, rssi):
         d = 10**((-60-(rssi))/(10*2.5))
         return d
    
    def aggregate_readings(self, readings):
        """
        Takes in a list of readings and returns some singular aggregate RSSI value
        """
        if len(readings) == 0:
            return None
        sorted_readings = list(sorted(readings))
        mid = len(sorted_readings) // 2
        if len(sorted_readings) % 2 == 0:
            return (sorted_readings[mid - 1] + sorted_readings[mid]) / 2
        else:
            return sorted_readings[mid]

    def localize_object_fingerprint(self, object_epc):
        cur_zone, tag_rssi = self.localize_reader(10)
        object_readings = {}

        candidates = list(range(self.zone_count))
        threshold = 5

        #ideally this is done until we have enough zone readings to be certain of object location
        # while some list of candidates has more than 1 element, 
        # where a candidate is a fingerprint that can be max distance d from current readings
        # this may just not terminate so static upper bound used
        while len(object_readings) < min(3, len(self.zone_count)) or len(candidates) > 1:
            print(f"localizing reader...")
            cur_zone, tag_rssi = self.localize_reader(10)
            print(f"Reader zone: {cur_zone}")

            #Finding distance to object from current zone
            readings = []
            def read_update(tag):
                epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
                if epc == object_epc:
                    readings.append(rssi)

            self.reader.start_reading(lambda tag: read_update(tag))
            while len(readings) < 10:
                sleep(1)
            self.reader.stop_reading()
            print(f"Zone: {cur_zone} found with the following readings: {readings}")
            object_readings[cur_zone] = self.aggregate_readings(readings)
            current_fingerprint = np.array([object_readings[zone] for zone in object_readings])

            new_candidates = []
            for old_candidate in candidates:
                old_candidate_fingerprint = self.zone_fingerprints[old_candidate][list(object_readings.keys())] #ensure that the order is the same
                if (abs(old_candidate_fingerprint - current_fingerprint) < threshold):
                    new_candidates.append(old_candidate)
            candidates = new_candidates
        
        if len(candidates) == 1:
            return candidates[0]

        fingerprints = {zone: self.zone_fingerprints[zone][list(object_readings.keys())] for zone in object_readings}
        cur_fingerprint = np.array([object_readings[zone] for zone in object_readings])
        return min(fingerprints, key=lambda zone: np.linalg.norm(cur_fingerprint - fingerprints[zone]))

    def localize_object_trilaterate(self, object_epc, min_num_readings):
        zone_to_readings = {}

        while (len(zone_to_readings) < 3):
            print(f"localizing reader...")
            cur_zone, _ = self.localize_reader(5)
            
            if cur_zone in zone_to_readings:
                continue

            print(f"Reader zone: {cur_zone}")

            #Finding distance to object from current zone
            readings = []
            def read_update(tag):
                epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
                if epc == object_epc:
                    readings.append(rssi)

            self.reader.start_reading(lambda tag: read_update(tag))
            while len(readings) < min_num_readings:
                sleep(1)
            self.reader.stop_reading()
            zone_to_readings[cur_zone] = readings

            print(f"Zone: {cur_zone} found with the following readings: {readings}")
            print(f"Looking for {3 - len(zone_to_readings)} more zones")
        
        # trilaterate
        centroid_positions = [self.zone_positions[zone] for zone in zone_to_readings]
        print(f"Centroid positions: {centroid_positions}")
        centroid_aggregate_readings = [self.aggregate_readings(zone_to_readings[zone]) for zone in zone_to_readings]

        centroid_distances = list(map(self.distance, centroid_aggregate_readings))
        print(f"Centroid distances: {centroid_distances}")

        def objective(reader_pos):
            return np.sum((np.linalg.norm(reader_pos - centroid_positions, axis=1) - centroid_distances)**2)

        initial_guess = np.mean(centroid_positions, axis=0)
        result = minimize(objective, initial_guess, method='L-BFGS-B')

        if result.success:
            estimated_position = result.x
            print(f"Estimated object position: {result}")
            return min(self.zone_positions, key=lambda zone: np.linalg.norm(self.zone_positions[zone] - estimated_position))
        else:
            print("Optimization failed:", result.message)
            return None


    # def localize_object(self, object_epc):
    #     eligible_zones = [i for i in range(self.zone_count)]

    #     while len(eligible_zones) > 1:
    #         reader_zone = self.localize_reader(10)

    #         #UPDATE THIS
    #         object_rssi_count = 0
    #         object_rssi_avg = 0
    #         object_min_rssi = float("inf")

    #         def read_update(tag):
    #             nonlocal object_rssi_count, object_rssi_avg, object_min_rssi
    #             epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
    #             if epc == object_epc:
    #                 object_min_rssi = min(rssi, object_min_rssi)
    #                 object_rssi_count += 1
    #                 object_rssi_avg += rssi

            
    #         self.reader.start_reading(lambda tag: read_update(tag))
    #         while object_rssi_count < 10:
    #             sleep(1)

    #         self.reader.stop_reading()

    #         # if (object_rssi_count):
    #         #     object_distance = self.distance((object_rssi_avg/object_rssi_count))
    #         #     print(f"Reader zone: {reader_zone}, Object distance: {object_distance}")

    #         if (object_min_rssi < float("inf")):
    #             print(f"Object min RSSI: {object_min_rssi}")
    #             object_distance = self.distance(object_min_rssi)

    #         for eligible_zone in self.zone_distance_map[reader_zone]:
    #             distance_range = self.zone_distance_map[reader_zone][eligible_zone]
    #             if distance_range[0] <= object_distance <= distance_range[1]:
    #                 print(f"Zone: {eligible_zone} Object distance: {object_distance}")
    #                 pass
    #             else:
    #                 eligible_zones.remove(eligible_zone)
    #         pass
        
    #     return eligible_zones[0]
    

if __name__ == "__main__":
    system = RssiLocalizationBase()
    object_id = "E23456780000000000000006"
    # print(f"Reader zone: {system.localize_reader(100)}")
    object_zone = system.localize_object(object_id, 10)
    print(f"{object_id} located at ZONE: {object_zone}")

# current plan

# assign centroids and find reader by finding closest centroid

# then need to localize items, assuming 9/9 grid for now

# IDEA for object localization: assign every zone a map of all possible locatoins to every other zone
# by distance, then as localized reader moves around, eliminate every possible zone that doesn't fit
# into that distance estimation until one left