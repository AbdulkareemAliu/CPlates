import numpy as np
from scipy.optimize import minimize

# Convert RSSI to distance using path loss model
def rssi_to_distance(rssi, rssi_0=-70, n=2.0):
    return 10 ** ((rssi_0 - rssi) / (10 * n))

# Cost function for multilateration in 3D
def multilateration_cost(pos, anchors, distances):
    return sum((np.linalg.norm(pos - anchor) - d)**2 for anchor, d in zip(anchors, distances))

# Anchors: (x, y, z)
anchor1 = np.array([0.0, 0.0, 0.0])
anchor2 = np.array([1.0, 0.0, 0.0])
anchor3 = np.array([0.0, 1.0, 0.0])

# RSSI readings at each anchor
rssi1 = -50
rssi2 = -48
rssi3 = -52

# Convert RSSI to distance
d1 = rssi_to_distance(rssi1)
d2 = rssi_to_distance(rssi2)
d3 = rssi_to_distance(rssi3)

# Set up anchors and distances
anchors = [anchor1, anchor2, anchor3]
distances = [d1, d2, d3]

# Initial guess for position
initial_guess = np.array([0.5, 0.5, 0.5])

# Minimize cost function
result = minimize(multilateration_cost, initial_guess, args=(anchors, distances))

# Final estimated position
estimated_position = result.x
print("Estimated Position (x, y, z):", estimated_position)