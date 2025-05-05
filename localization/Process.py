
#This code will need to replace IB localization class in system.py, should localize tags based on 
#signal strength to reader. also need to figure out how to find where reader is based on anchor tags


import mercury
from datetime import datetime, timezone
from time import sleep


class RssiLocalizationBase:
    def __init__(self):
        self.zone_count = 2
        self.zones = {"E23456780000000000000031": 0,
                      "E23456780000000000000023": 1}
        
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
        
        self.reader = mercury.Reader("tmr:///dev/cu.usbserial-AQ00WAJ1")
        self.reader.set_region("NA")
        self.reader.set_read_plan([1], "GEN2", read_power=3000)
    pass 

    def localize_reader(self, tag_count):
        """
        Runs asynchronous reading: will continuously read tags until you hit CTRL-C, and saves the results to a csv, and returns a pandas dataframe of the data
        """
        tag_rssi_count = {zone_tag: 0 for zone_tag in self.zones}
        tag_rssi_avg = {zone_tag: 0 for zone_tag in self.zones}

        def read_update(tag):
            epc, rssi = tag.epc.decode("utf-8"), tag.rssi
            
            if epc in self.zones:
                tag_rssi_count[epc] += 1
                tag_rssi_avg[epc] += rssi
        
        self.reader.start_reading(lambda tag: read_update(tag))
        while min(tag_rssi_count.values()) < tag_count:
            sleep(1)

        self.reader.stop_reading()
        #Find zone
        for zone_tag in self.zones:
            if (tag_rssi_count[zone_tag] > 0):
                tag_rssi_avg[zone_tag] /= tag_rssi_count[zone_tag]
        
        max_rssi_tag = max(tag_rssi_avg, key=tag_rssi_avg.get)
        zone = self.zones[max_rssi_tag]
        return zone
    
    def distance(self, rssi):
         d = 10**((-45-(rssi))/(10*2.5))
         return d
    
    def localize_object(self, object_epc):
        eligible_zones = [i for i in range(self.zone_count)]

        while len(eligible_zones) > 1:
            reader_zone = self.localize_reader(10)

            #UPDATE THIS
            object_rssi_count = 0
            object_rssi_avg = 0

            def read_update(tag):
                nonlocal object_rssi_count, object_rssi_avg
                epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
                print(f"epc: {epc}, rssi: {rssi}")
                if epc == object_epc:
                    object_rssi_count += 1
                    object_rssi_avg += rssi

            
            self.reader.start_reading(lambda tag: read_update(tag))
            while object_rssi_count < 10:
                sleep(1)

            self.reader.stop_reading()

            if (object_rssi_count):
                object_distance = self.distance((object_rssi_avg/object_rssi_count))
                print(f"Reader zone: {reader_zone}, Object distance: {object_distance}")

            for eligible_zone in self.zone_distance_map[reader_zone]:
                distance_range = self.zone_distance_map[reader_zone][eligible_zone]
                if distance_range[0] <= object_distance <= distance_range[1]:
                    print(f"Zone: {eligible_zone} Object distance: {object_distance}")
                    pass
                else:
                    eligible_zones.remove(eligible_zone)
            pass
        
        return eligible_zones[0]
    

if __name__ == "__main__":
    system = RssiLocalizationBase()
    object_id = "E2345678000000000000001A"
    object_zone = system.localize_object(object_id)
    print(f"{object_id} located at ZONE: {object_zone}")

# current plan

# assign centroids and find reader by finding closest centroid

# then need to localize items, assuming 9/9 grid for now

# IDEA for object localization: assign every zone a map of all possible locatoins to every other zone
# by distance, then as localized reader moves around, eliminate every possible zone that doesn't fit
# into that distance estimation until one left