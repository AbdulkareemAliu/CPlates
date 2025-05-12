#This code will need to replace IB localization class in system.py, should localize tags based on 
#signal strength to reader. also need to figure out how to find where reader is based on anchor tags

import mercury
import numpy as np
from scipy.optimize import minimize
from datetime import datetime, timezone
from time import sleep

import pyttsx3
from LLM import LLMHandler
from Speech import SpeechHandler

class RssiLocalizationBase:
    def __init__(self):
        self.start_stop_key = "p"
        # self.speech_handler = SpeechHandler("models/vosk-model-small-en-us-0.15", self.start_stop_key)
        self.llm_handler = LLMHandler()
        self.engine = pyttsx3.init()

        self.zones = {
                        "E135204700000000000000CA": 0,
                        "E200001D080200251960084D": 0,
                        "E200001D080200261960060A": 1,
                        "E2000016360300F521004151": 1,
                        "E20000163603007321004144": 2,
                        "E200001D080200271960084E": 2,
                        "E200001D080200281960060B": 3,
                        "E23456780000000000000023": 3,
                        "E200001D080200291960084F": 4,
                        "E23456780000000000000006": 4,
                        
                      }

        self.object_epcs = set(["E23456780000000000000031", "E2000016360300F521004151"])

        self.zone_count = len(set(self.zones.values()))
        
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
            1: [0, 10.5],
            2: [13, 10.5],
            3: [13, 0],
            4: [17.5, 5.25]
        }

        self.zone_fingerprints = {
            0: np.array([-50, -60, -70]),
            1: np.array([-60, -50, -90]),
            2: np.array([-70, -90, -50])
        }
        
        self.reader = mercury.Reader("tmr:///dev/cu.usbserial-A400F2CW")
        self.reader.set_region("NA")
        self.reader.set_read_plan([1], "GEN2", read_power=3000)

    def localize_reader(self, tag_count):
        """
        Runs asynchronous reading: will continuously read tags until you hit CTRL-C, and saves the results to a csv, and returns a pandas dataframe of the data
        """
        tag_rssi = [[] for zone_i in range(self.zone_count)]

        def read_update(tag):
            epc, rssi = tag.epc.decode("utf-8"), tag.rssi

            if epc in self.zones:
                tag_rssi[self.zones[epc]].append(rssi)
        
        self.reader.start_reading(lambda tag: read_update(tag))
        while min([len(vals) for vals in tag_rssi]) < tag_count:
            print({zone_i: len(zone_rssi_vals) for zone_i, zone_rssi_vals in enumerate(tag_rssi)})
            sleep(3)

        self.reader.stop_reading()
        #Find zone
        tag_rssi_avg = {zone_i: sum(zone_rssi_vals) / len(zone_rssi_vals)
                        for zone_i, zone_rssi_vals in enumerate(tag_rssi)}
        
        max_rssi_zone = max(range(self.zone_count), key=lambda i: max(tag_rssi[i]))
        return max_rssi_zone, tag_rssi
    
    def distance(self, rssi):
         d = 10**((-55-(rssi))/(10*2.5))
         return d * 3.28084 # Convert to feet
    
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
            print(f"Localizing reader")
            cur_zone, tag_rssi = self.localize_reader(10)
            print(f"Reader zone: {cur_zone}")

            #Finding distance to object from current zone
            readings = []
            def read_update(tag):
                epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
                if epc == object_epc:
                    readings.append(rssi)

            self.reader.start_reading(lambda tag: read_update(tag))
            while len(readings) < 100:
                sleep(3)
            self.reader.stop_reading()
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

        self.engine.say(f"localizing reader...")
        self.engine.runAndWait()

        while (len(zone_to_readings) < 3):
            cur_zone, _ = self.localize_reader(5)
            
            if cur_zone in zone_to_readings:
                continue

            self.engine.say(f"You are in zone {cur_zone}. Now localizing object...")
            self.engine.runAndWait()

            #Finding distance to object from current zone
            readings = []
            def read_update(tag):
                epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
                if epc == object_epc:
                    readings.append(rssi)

            self.reader.start_reading(lambda tag: read_update(tag))

            while len(readings) < min_num_readings:
                print(len(readings))
                sleep(2)

            self.reader.stop_reading()
            zone_to_readings[cur_zone] = readings

            print(f"Zone: {cur_zone} found with the following readings: {readings}, aggregate: {self.aggregate_readings(readings)}")
            self.engine.say(f"Found the object! Looking for {3 - len(zone_to_readings)} more zones.")
            self.engine.runAndWait()
        
        # trilaterate
        centroid_positions = [self.zone_positions[zone] for zone in zone_to_readings]
        print(f"Centroid positions: {centroid_positions}")
        centroid_aggregate_readings = [self.aggregate_readings(zone_to_readings[zone]) for zone in zone_to_readings]

        centroid_distances = list(map(self.distance, centroid_aggregate_readings))
        print(f"Centroid distances: {centroid_distances}")

        def objective(object_pos):
            return np.sum((np.linalg.norm(object_pos - centroid_positions, axis=1) - centroid_distances)**2)

        initial_guess = np.mean(centroid_positions, axis=0)
        result = minimize(objective, initial_guess, method='L-BFGS-B')

        if result.success:
            estimated_position = result.x
            print(f"Estimated object position: {result}")
            found_zone = min(self.zone_positions, key=lambda zone: np.linalg.norm(self.zone_positions[zone] - estimated_position))
            self.engine.say(f"Object is in zone {found_zone}.")
            self.engine.runAndWait()
            return found_zone
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
    #             sleep(3)

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
    

    def log(self, log_extra_stats=False, epc_to_track=None):
        rssi_vals = []
        def callback(tag):
            epc, rssi = tag.epc.decode("utf-8"), tag.rssi
            if epc_to_track is None:
                print(f"Tag EPC: {epc}, RSSI: {rssi}")
            elif (tag.epc.decode("utf-8") == epc_to_track):
                rssi_vals.append(rssi)
                if len(rssi_vals) > 0:
                    print("RSSI: ", rssi)
                    if log_extra_stats:
                        median_rssi = sorted(rssi_vals)[len(rssi_vals) // 2]
                        average_rssi = sum(rssi_vals) / len(rssi_vals)
                        print(f"Average RSSI: {average_rssi}")
                        print(f"Median RSSI: {median_rssi}")
                        print(f"Min RSSI: {min(rssi_vals)}")
                        print(f"Max RSSI: {max(rssi_vals)}")

        self.reader.start_reading(callback)
        while True:
            sleep(3)

        system.reader.stop_reading()

    def record_and_query(self):
        query = self.speech_handler.record()
        # query = input("Enter your query: ")

        if query:
            response = self.llm_handler.query_llm(query)
            
            if response == "None" or response is None:
                print("No response from LLM.")
                return None

            print(response)

            item, id = response.split(", ")
            item = item.strip()
            id = id.strip()
            
            if id not in self.object_epcs:
                print(self.object_epcs)
                print("ID not found in zones.")
                return None

            print("User Query:", query)
            print("LLM Item Response:", item)
            print("LLM Item ID:", id)

            return id
        else:
            print("No query recorded.")
            return None


if __name__ == "__main__":
    system = RssiLocalizationBase()

    # system.log(log_extra_stats=False)
    # object_id = system.record_and_query() # "E23456780000000000000031"
    object_id = "E23456780000000000000031"
    print("Looking for: ", object_id)
    if object_id is None:
        print("No object ID found.")
    else:
        # print(f"Reader zone: {system.localize_reader(100)}")
        object_zone = system.localize_object_trilaterate(object_id, 5)
        print(f"{object_id} located at ZONE: {object_zone}")

# current plan

# assign centroids and find reader by finding closest centroid

# then need to localize items, assuming 9/9 grid for now

# IDEA for object localization: assign every zone a map of all possible locatoins to every other zone
# by distance, then as localized reader moves around, eliminate every possible zone that doesn't fit
# into that distance estimation until one left