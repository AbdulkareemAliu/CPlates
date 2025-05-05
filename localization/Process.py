
#This code will need to replace IB localization class in system.py, should localize tags based on 
#signal strength to reader. also need to figure out how to find where reader is based on anchor tags


from localization.Reader import ReadingData, ThingMagic
from datetime import datetime, timezone
from time import sleep


class RssiLocalizationBase:
    def __init__(self):
        self.zone_count = 2
        self.zones = {"E135204700000000000000CA": 0,
                      "E23456780000000000000031": 1}
        
        #Maps each zone to the possible distances to every other zone
        #e.g. for zone 0, distances found of 0 to 5 could correspond to zone 1
        self.zone_distance_map = {
            0: {
                0: (0, 3),
                1: (0, 5)
            },
            1: {
                0: (0, 5),
                1: (0, 3)
            }
        }
        
        self.reader = ThingMagic()
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
        try:
            while min(tag_rssi_count.values()) < tag_count:
                sleep(1)
        except KeyboardInterrupt:
            self.reader.stop_reading()
            print('Done :)')
            pass

        #Find zone
        for zone_tag in self.zones:
            tag_rssi_avg[zone_tag] /= tag_rssi_count[zone_tag]
        
        max_rssi_tag = max(tag_rssi_avg, key=tag_rssi_avg.get)
        zone = self.zones[max_rssi_tag]
        return zone
    
    def distance(self, rssi):
         d = 10**((-70-(rssi))/(10*2.5))
         return d
    
    def localize_object(self, object_epc):
        eligible_zones = [i for i in range(self.zone_count)]

        while len(eligible_zones) > 1:
            reader_zone = self.localize_reader(10)

            #UPDATE THIS
            object_rssi_count = 0
            object_rssi_avg = 0

            def read_update(tag):
                epc, rssi = tag.epc.decode("utf-8"), tag.rssi
                
                if epc == object_epc:
                    object_rssi_count += 1
                    object_rssi_avg += rssi

            
            self.reader.start_reading(lambda tag: read_update(tag))
            try:
                while object_rssi_count < 10:
                    sleep(1)
            except KeyboardInterrupt:
                self.reader.stop_reading()
                print('Done :)')
                pass
            
                
            object_distance = self.distance((object_rssi_avg/object_rssi_count))

            for eligible_zone in self.zone_distance_map[reader_zone]:
                range = self.zone_distance_map[reader_zone][eligible_zone]
                if range[0] <= object_distance <= range[1]:
                    pass
                else:
                    eligible_zones.remove(eligible_zone)
            pass
        
        return eligible_zones[0]
    

if __name__ == "__main__":
    system = RssiLocalizationBase()
    object_id = "ABC"
    object_zone = system.localize_object(object_id)
    print(f"{object_id} located at ZONE: {object_zone}")

# current plan

# assign centroids and find reader by finding closest centroid

# then need to localize items, assuming 9/9 grid for now

# IDEA for object localization: assign every zone a map of all possible locatoins to every other zone
# by distance, then as localized reader moves around, eliminate every possible zone that doesn't fit
# into that distance estimation until one left