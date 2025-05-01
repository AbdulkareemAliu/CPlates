import numpy as np
from collections import defaultdict
from Reader import ThingMagic
from scipy.optimize import minimize 

class Localizer: 
    def __init__(
            self, 
            centroid_epc_to_position: dict[str, tuple[int, int]],
            object_epc: str
    ):
        self.centroid_epcs = list(centroid_epc_to_position.keys())
        self.centroid_epc_to_position = centroid_epc_to_position

        self.reader = ThingMagic(self.centroid_epcs + [object_epc])


    def find_nearest_centroid(self):
        centroid_readings = [
            self.reader.anchor_tags_rssi_avg[centroid]
            for centroid in self.centroid_epcs
        ]

        centroid_id = max(range(len(self.centroid_epcs)), key=lambda i: centroid_readings[i])
        return self.centroid_epcs[centroid_id]

    def localize_tag(self, centroid_epcs, object_epc):
        centroid_to_distance = defaultdict(list)

        while (len(centroid_to_distance) < 5):
            self.reader.async_reading(True, 10)
            cur_centroid = self.localize_reader()
            object_rssi = self.reader.anchor_tags_rssi_avg[object_epc]

            centroid_to_distance[cur_centroid].append(object_rssi)

    def distance(self, rssi):
        d = 10**((-60-(rssi))/(10*3.0))
        return d
    
    def trilaterate(self, centroid_to_distance: dict[str, int]):
        distances = [
            centroid_to_distance[centroid] 
            for centroid in self.centroid_epcs 
            if centroid in centroid_to_distance
        ]
        anchor_positions = [
            self.centroid_epc_to_position[centroid] 
            for centroid in self.centroid_epcs 
            if centroid in centroid_to_distance
        ]

        def objective(reader_pos):
            return np.sum((np.linalg.norm(reader_pos - anchor_positions, axis=1) - distances)**2)

        initial_guess  = np.mean(anchor_positions, axis=0)
        result = minimize(objective, initial_guess, method='L-BFGS-B')

        if result.success:
            return [result.x, result.y]
        else:
            print("Optimization failed:", result.message)




if __name__ == "__main__":
    tag_epcs = [
            # "D4C3204700000000000000C4",
            "E135204700000000000000CA",
            "E23456780000000000000031",
            # "E23456780000000000000023"
        ]

    localizer = Localizer(tag_epcs)
    print(localizer.localize_reader())