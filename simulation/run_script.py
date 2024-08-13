import sys
import os
from PyQt5.QtWidgets import QApplication

# Add parent directories to the Python path
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')

# Import custom modules
from Central_Controller.CTGUI import CentralControllerGUI, read_map_file

def run_algo(algo_name, map_path, scen_path):
    
    # Create a QApplication instance
    app = QApplication(sys.argv)
    
    # Create an instance of CentralControllerGUI
    ex = CentralControllerGUI(cell_size=30)
    
    # Process the UAV batch scenario
    ex.processUAVBatch(scen_path)
    
    # Read the map file
    (width, height), obstacles, lines = read_map_file(map_path)
    
    # Set map properties in the CentralControllerGUI instance
    ex.map_width = width
    ex.map_height = height
    ex.map_obstacles = obstacles
    ex.mapLoaded = True
    
    # List of time budgets to iterate over
    #time_budgets = [16, 64, 256, 400] 
    time_budgets = [32]
    
    for time_budget in time_budgets:
        print(f"Running generatePaths_test with time budget: {time_budget}")
        ex.generatePaths_test(algo_name, time_budget)
    


# Run the algorithm if the script is executed directly
if __name__ == "__main__":
    # Replace these paths with the actual paths to your .map and .scen files
    map_path = "/home/amath/Documents/Dymudrop/maps/Berlin/Berlin_1_256.map"
    scen_path = "/home/amath/Documents/Dymudrop/maps/Berlin/Berlin_1_256-random-1.scen"
    
    run_algo("AlphaUCB", map_path, scen_path)


