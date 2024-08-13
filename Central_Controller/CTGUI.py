import tkinter as tk
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import sys
sys.path.insert(0,'..')
sys.path.insert(0,'../..')
sys.path.insert(0,'../../..')
import sys

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QFormLayout, QLabel, QDialog, QHBoxLayout,QFrame,QFileDialog,QGraphicsEllipseItem
from PyQt5.QtGui import QPixmap , QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem,QFileDialog
from PyQt5.QtGui import QColor,QPen,QBrush
from PyQt5.QtCore import QRectF,QPointF,QLineF
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from Central_Controller.EnvCluster import *
from utils.plot import *
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

def read_map_file1(file_path):
    with open(file_path, 'r') as file:
        map_data = file.readlines()
    return map_data

def read_map_file(map_file_path):
    with open(map_file_path, 'r') as map_file:
        lines = map_file.readlines()

    # Initialize variables to store map dimensions
    height = width = 0

    # Extract dimensions
    for line in lines:
        if line.startswith("height"):
            height = int(line.split()[1])
        elif line.startswith("width"):
            width = int(line.split()[1])
        elif line.startswith("map"):
            # The actual map data starts from the next line
            map_start_index = lines.index(line) + 1
            break

    # Initialize obstacles list
    obstacles = []

    # Parse the grid to find obstacles
    for y, line in enumerate(lines[map_start_index:map_start_index + height]):
        for x, char in enumerate(line.strip()):
            # Here we consider 'T' as impassable. '@', 'O' as out of bounds, and 'W' as not passable from terrain
            if char in {'@', 'O', 'T', 'W'}:
                obstacles.append((x, y))

    return (width, height), obstacles,lines


class AddUAVDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add UAV(s)')
        
        layout = QVBoxLayout()
        
        # Button for adding a single UAV
        self.addSingleUAVBtn = QPushButton('Add Single UAV', self)
        self.addSingleUAVBtn.clicked.connect(self.addSingleUAV)
        layout.addWidget(self.addSingleUAVBtn)
        
        # Button for adding UAVs from a file
        self.addUAVBatchBtn = QPushButton('Add UAVs from File', self)
        self.addUAVBatchBtn.clicked.connect(self.addUAVsBatch)
        layout.addWidget(self.addUAVBatchBtn)
        
        self.setLayout(layout)
    
    def addSingleUAV(self):
        uav_name, ok1 = QInputDialog.getText(self, 'Add Single UAV', 'Enter UAV name:')
        if ok1 and uav_name:
            initial_position, ok2 = QInputDialog.getText(self, 'Add Single UAV', 'Enter start position (e.g., x,y):')
            if ok2:
                target_position, ok3 = QInputDialog.getText(self, 'Add Single UAV', 'Enter goal position (e.g., x,y):')
                if ok3:
                    self.parent().addUAV(uav_name, initial_position, target_position)

    
    def addUAVsBatch(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open UAV Scenario File", "", "Scenario files (*.scen)")
        if file_path:
            self.parent().processUAVBatch(file_path)


class CentralControllerGUI(QWidget):
    def __init__(self, cell_size=15):
        super().__init__()
        self.initUI()
        self.tasks = []
        self.clusters = {}
        self.mapLoaded = False
        self.map_width = None
        self.map_height = None
        self.map_obstacles = []
        self.cell_size = cell_size
        self.uavs = []
        self.dynamicItems = []
        self.colors = [QColor('red'), QColor('blue'), QColor('cyan'), QColor('magenta'), QColor('yellow')]

    def initUI(self):
        self.setWindowTitle('Central Controller GUI for UAVs')

        screen = QApplication.primaryScreen()
        screen_size = screen.size()

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)

        imageLabel = QLabel(self)
        pixmap = QPixmap('image/uav.png')
        imageLabel.setPixmap(pixmap)
        imageLabel.setScaledContents(True)
        imageLabel.setFixedSize(screen_size.width() // 4, screen_size.height() // 10)
        title = QLabel('Välkommen till flygledningstjänsten!!!')
        title.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(title)
        mainLayout.addWidget(imageLabel, alignment=Qt.AlignCenter)

        columnsLayout = QHBoxLayout()
        leftColumn = QVBoxLayout()

        self.addUAVBtn = QPushButton('Add UAV', self)
        leftColumn.addWidget(self.addUAVBtn)
        self.listClustersBtn = QPushButton('List Clusters')
        self.removeTaskBtn = QPushButton('Remove Cluster')
        leftColumn.addWidget(self.removeTaskBtn)
        self.addNoFlyZoneBtn = QPushButton('Add No-Fly Zone')
        self.generatePathsBtn = QPushButton('Generate Paths')
        self.generateMetricsBtn = QPushButton('Generate Metrics')
        leftColumn.addWidget(self.listClustersBtn)
        self.loadMapBtn = QPushButton('Load Map')
        leftColumn.addWidget(self.loadMapBtn)
        self.loadMapBtn.clicked.connect(self.loadAndDisplayMap)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.addUAVBtn)
        buttonLayout.addWidget(self.removeTaskBtn)
        buttonLayout2 = QHBoxLayout()
        buttonLayout2.addWidget(self.addNoFlyZoneBtn)
        buttonLayout2.addWidget(self.generatePathsBtn)

        self.addUAVBtn.clicked.connect(self.openAddUAVDialog)
        self.removeTaskBtn.clicked.connect(self.removeTask)
        self.addNoFlyZoneBtn.clicked.connect(self.addNoFlyZone)
        self.generatePathsBtn.clicked.connect(self.generatePaths)
        self.generateMetricsBtn.clicked.connect(self.generateMetrics)
        self.listClustersBtn.clicked.connect(self.listClusters)

        leftColumn.addLayout(buttonLayout)
        leftColumn.addLayout(buttonLayout2)
        leftColumn.addWidget(self.generateMetricsBtn)

        rightColumn = QVBoxLayout()
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)

        self.view.resetTransform()
        self.view.setScene(self.scene)
        self.view.setFixedSize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.7))
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setRenderHint(QPainter.Antialiasing)
        rightColumn.addWidget(self.view, alignment=Qt.AlignCenter)

        columnsLayout.addLayout(leftColumn)
        columnsLayout.addLayout(rightColumn)
        mainLayout.addLayout(columnsLayout)
        self.setLayout(mainLayout)
        
    # Method to clear only dynamic items from the scene
    def clearDynamicItems(self):
        for item in self.dynamicItems:
            self.scene.removeItem(item)
        self.dynamicItems.clear() 

    def openAddUAVDialog(self):
        dialog = AddUAVDialog(self)
        dialog.exec_()

    def addUAV(self, uav_id, uav_name, initial_position, target_position, map_file, width, height, optimal_length):
        start_pos = list(map(int, initial_position.split(',')))
        goal_pos = list(map(int, target_position.split(',')))
        uav_data = {
            'id': uav_id, 
            'name': uav_name,
            'start': start_pos,
            'goal': goal_pos,
            'map_file': map_file,
            'width': width,
            'height': height,
            'optimal_length': float(optimal_length)
        }
        self.uavs.append(uav_data)
        #print(f"Added UAV: {uav_data}")

    
    def processUAVBatch(self, file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()

        for line in lines[1:]:  # Skip header
            parts = line.strip().split()
            if len(parts) >= 9:
                uav_id = int(parts[0]) 
                map_file = parts[1]
                width = parts[2]
                height = parts[3]
                start_x = parts[4]
                start_y = parts[5]
                goal_x = parts[6]
                goal_y = parts[7]
                optimal_length = float(parts[8])

                uav_name = f"UAV_{uav_id}_{start_x}_{start_y}_to_{goal_x}_{goal_y}"
                initial_position = f"{start_x},{start_y}"
                target_position = f"{goal_x},{goal_y}"
                
                self.addUAV(uav_id, uav_name, initial_position, target_position, map_file, width, height, optimal_length)




    def listClusters(self):
        if not self.tasks:
            QMessageBox.information(self, "List Clusters", "No cluster added yet.")
            return
        
        message = "List of Clusters:\n"
        for idx, task in enumerate(self.tasks, start=1):
            message += (f"{idx}. Task Name: {task['task_name']}, Initial Position: {task['start']}, "
                        f"Target Position: {task['goal']}\n")
        
        QMessageBox.information(self, "List Clusters", message)

    
    def removeTask(self):
        if not self.tasks:
            QMessageBox.information(self, "Remove Cluster", "No clusters available to remove.")
            return

        # Use dictionary key access instead of attribute access
        task_names = [task['task_name'] for task in self.tasks]
        task_name, ok = QInputDialog.getItem(self, "Remove Cluster", "Select cluster to remove:", task_names, 0, False)

        if ok and task_name:
            # Find and remove the selected task using list comprehension and the `task_name` key
            self.tasks = [task for task in self.tasks if task['task_name'] != task_name]
            QMessageBox.information(self, "Remove cluster", f"Cluster '{task_name}' removed successfully.")


    def displayMap(self, map_data):
        self.scene.clear()  # Clear the scene before displaying a new map
        for y, row in enumerate(map_data):
            for x, char in enumerate(row.strip()):
                if char == '.':
                    color = QColor("green")  # Open space
                elif char in {'#','@', 'O', 'T', 'W'}:
                    color = QColor("black")  # Obstacle
                else:
                    continue
                rect = QRectF(x*self.cell_size, y*self.cell_size, self.cell_size, self.cell_size)
                self.scene.addRect(rect, brush=color)
                



    def loadAndDisplayMap(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Map File", "", "Map files (*.map)")
        if file_path:
            map_size, obstacles, lines = read_map_file(file_path)
            self.map_width, self.map_height = map_size
            self.map_obstacles = obstacles

            self.scene.setSceneRect(0, 0, self.map_width * self.cell_size, self.map_height * self.cell_size)
            self.scene.clear()

            for x in range(self.map_width):
                for y in range(self.map_height):
                    rect = self.scene.addRect(x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size)
                    rect.setBrush(QColor('green'))
                    rect.setPen(QColor('black'))

            for (x, y) in self.map_obstacles:
                rect = self.scene.addRect(x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size)
                rect.setBrush(QColor('black'))
                rect.setPen(QColor('black'))

            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.mapLoaded = True

        


    def addNoFlyZone(self):
        # Placeholder for adding no-fly zone logic
        print("Adding no-fly zone...")

    
    def gather_submaps(self,directory_path):
 
        submaps = []
        map_files = [f for f in os.listdir(directory_path) if f.endswith('.map')]
        scen_files = set(os.listdir(directory_path))  
        for map_file in map_files:
            base_name = map_file[:-4]  
            scen_file = f"{base_name}.scen"
            if scen_file in scen_files:
                submaps.append({
                    "map": os.path.join(directory_path, map_file),
                    "scen": os.path.join(directory_path, scen_file)
                })
        return submaps
    

    # Function to call the executable
    def run_planner(self,cpp_exec, map_file, scen_file, output_name, k_value, time_limit, pathstxt, alg, seed):
        command = [
            cpp_exec, "-m", map_file, "-a", scen_file, "-o", output_name,
            "-k", str(k_value), "-t", str(time_limit), "--outputPaths", pathstxt,
            "--banditAlgo", alg, "--neighborCandidateSizes", "5", "--seed",str(seed),"--lambdaDecay", "5"
        ]
        try:
            result = subprocess.run(
                command,
                #shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True  # Raises CalledProcessError on non-zero exit status
            )
            return {"success": True, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"success": False, "output": e.stderr}
    

    def generatePaths_test(self,algo, time_budget):
        
        uavs = self.uavs
        #print(uavs)

        obstacles = self.map_obstacles 

        alg=algo
      
        manager = UAVClusterManager(uavs,(self.map_width,self.map_height), obstacles)
        print("Initial clusters:")
        clusters = manager.get_sub_maps()
        #print("clusters",clusters)
        

        # Generate submaps and store the number of UAVs for each
        uav_counts = {}
        for cluster_id, cluster_info in clusters.items():
            uav_counts[cluster_id] = manager.create_map_file(cluster_id, cluster_info)

        # Paths to the C++ executable and directory containing the submap files
        cpp_executable = "../models/cluster-MAPF/dymab-mapf/dymab"
        submap_path = '../simulation'
        
    
        # Use the function to get submaps
        submaps = self.gather_submaps(submap_path)
        #submaps = [{'map': '../simulation/image/submap_18.map', 'scen': '../simulation/image/submap_18.scen'}]
        
        
        # Use ThreadPoolExecutor to run multiple instances of the C++ executable in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for sm in submaps:
                base_name = os.path.basename(sm["map"]).replace(".map", "")
                cluster_id = int(base_name.split('_')[-1])  # Assuming naming like "submap_0.map"
                k_value = uav_counts.get(cluster_id, 1)  
                print("number",k_value)
                future = executor.submit(
                    self.run_planner, cpp_executable, sm["map"], sm["scen"], "test", k_value, time_budget, f"paths_cluster{cluster_id}.txt",alg,0
                )
                futures.append(future)

            for future in futures:
                result = future.result()  # Wait for the process to complete
                if result["success"]:
                    print(f"Submap processed successfully:\n{result['output']}")
                else:
                    print(f"Error processing submap:\n{result['output']}")

        
        input_csv = '../simulation/test-LNS.csv'
        output_csv = '../simulation/image/output_file.csv'
        ## process sub_maps stats for evaluation
        process_csv(input_csv, output_csv)
        
        ## remove .map and .scen files after planning
        for file_name in os.listdir(submap_path):
            if file_name.endswith('.map') or file_name.endswith('.scen') or file_name.endswith('.txt') or file_name.endswith('.csv'):
                file_path = os.path.join(submap_path, file_name)
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except OSError as e:
                    print(f"Error removing file {file_path}: {e}")

       

    def generatePaths(self):
        # Check if a map is loaded
        if not self.mapLoaded:
            QMessageBox.warning(self, "Error", "Please load a map before generating paths.")
            return
        

        if not self.uavs:
            QMessageBox.warning(self, "Error", "No UAV available to generate paths for.")
            return
        
        uavs = self.uavs
        #print(uavs)

        obstacles = self.map_obstacles 

        algorithms = ["AlphaUCB", "EpsilonGreedy", "dymab","LNS2"]
        cluster_algorithms = ["AlphaUCB", "EpsilonGreedy"]
        alg, ok = QInputDialog.getItem(self, "Select algo", "Select algorithm to run:", algorithms, 0, False)

        if alg=="CBS":
            ## get environment data
            dimension = [self.map_width, self.map_height]  
            obstacles = self.map_obstacles 
            # Initialize the environment for CBS
            env = Environment(dimension, uavs, obstacles)
            # Initialize and run CBS
            cbs = CBS(env)
            solution = cbs.search()
        
            if not solution:
                QMessageBox.information(self, "Error", "Unable to generate paths for all UAVs.")
            else:
                print("Generated Paths:", solution) 

        elif alg in cluster_algorithms:
            manager = UAVClusterManager(uavs,(self.map_width,self.map_height), obstacles)
            print("Initial clusters:")
            clusters = manager.get_sub_maps()
            #print("clusters",clusters)
            

            # Generate submaps and store the number of UAVs for each
            uav_counts = {}
            for cluster_id, cluster_info in clusters.items():
                uav_counts[cluster_id] = manager.create_map_file(cluster_id, cluster_info)

            # Paths to the C++ executable and directory containing the submap files
            cpp_executable = "../models/cluster-MAPF/dymab-mapf/dymab"
            submap_path = '../simulation'
            
        
            # Use the function to get submaps
            submaps = self.gather_submaps(submap_path)
            #submaps = [{'map': '../simulation/image/submap_18.map', 'scen': '../simulation/image/submap_18.scen'}]
            
            
            # Use ThreadPoolExecutor to run multiple instances of the C++ executable in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for sm in submaps:
                    base_name = os.path.basename(sm["map"]).replace(".map", "")
                    cluster_id = int(base_name.split('_')[-1])  # Assuming naming like "submap_0.map"
                    k_value = uav_counts.get(cluster_id, 1)  
                    print("number",k_value)
                    future = executor.submit(
                        self.run_planner, cpp_executable, sm["map"], sm["scen"], "test", k_value, 20, f"paths_cluster{cluster_id}.txt",alg,0
                    )
                    futures.append(future)

                for future in futures:
                    result = future.result()  # Wait for the process to complete
                    if result["success"]:
                        print(f"Submap processed successfully:\n{result['output']}")
                    else:
                        print(f"Error processing submap:\n{result['output']}")

            
            input_csv = '../simulation/test-LNS.csv'
            output_csv = '../simulation/image/output_file.csv'
            ## process sub_maps stats for evaluation
            process_csv(input_csv, output_csv)
            
            ## remove .map and .scen files after planning
            for file_name in os.listdir(submap_path):
                if file_name.endswith('.map') or file_name.endswith('.scen') or file_name.endswith('.txt') or file_name.endswith('.csv'):
                    file_path = os.path.join(submap_path, file_name)
                    try:
                        os.remove(file_path)
                        print(f"Removed file: {file_path}")
                    except OSError as e:
                        print(f"Error removing file {file_path}: {e}")



    def display_clusters_and_submaps(self, clusters):
        self.clearDynamicItems()  # Clear previous dynamic items

        for cluster_id, cluster_info in clusters.items():
            color = self.colors[cluster_id % len(self.colors)]  # Cycle through predefined colors

            # Draw UAVs in this cluster
            for uav in cluster_info['uavs']:
                self.draw_uav_with_offset(uav['start'], color, cluster_id)
                self.draw_uav_with_offset(uav['goal'], color, cluster_id)

            # Draw bounding box for the cluster
            self.draw_bounding_box_with_offset(cluster_info, color)

    def draw_uav_with_offset(self, position, color, cluster_id):
        offset = self.cell_size * 4  # Apply offset to position
        ellipse = QGraphicsEllipseItem(position[0] * self.cell_size , position[1] * self.cell_size + offset, self.cell_size, self.cell_size)
        ellipse.setBrush(color)
        self.scene.addItem(ellipse)
        self.dynamicItems.append(ellipse)  # Track as a dynamic item for later removal

    def draw_bounding_box_with_offset(self, cluster_info, color):
        offset = self.cell_size * 4  # Apply offset to position, not size
        
        # Retrieve the bounding box directly from cluster_info
        bounding_box = cluster_info['bounding_box']
        min_x, min_y, max_x, max_y = bounding_box['min_x'], bounding_box['min_y'], bounding_box['max_x'], bounding_box['max_y']
        
        # Calculate width and height based on the bounding box coordinates
        width = (max_x - min_x + 1) * self.cell_size
        height = (max_y - min_y + 1) * self.cell_size

        # Calculate the position of the bounding box including the offset
        rect = QGraphicsRectItem(min_x * self.cell_size, (min_y * self.cell_size) + offset, width, height)
        rect.setPen(QPen(color, 2))  # Set color and line width for the bounding box
        self.scene.addItem(rect)
        self.dynamicItems.append(rect)  # Track as a dynamic item for later removal



