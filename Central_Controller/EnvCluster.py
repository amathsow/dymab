from sklearn.cluster import OPTICS
import numpy as np
from collections import defaultdict

class UAVClusterManager:
    def __init__(self, uavs, map_size, obstacles, min_samples=2, xi=0.1, min_cluster_size=0.01):
        """
        Initialize with a list of UAVs, each having a 'name', 'start', and 'goal' position,
        and the overall map size.
        """
        self.uavs = uavs
        self.map_size = map_size
        self.obstacles = obstacles
        self.min_samples = min_samples
        self.xi = xi
        self.min_cluster_size = min_cluster_size
        self.sub_maps = {}
        self.labels = None
        self.data = None
        self._create_clusters_and_sub_maps()

    def _create_clusters_and_sub_maps(self):
        positions = []
        uav_identifiers = []  # To map each position back to its UAV

        for uav in self.uavs:
            positions.extend([uav['start'], uav['goal']])
            uav_identifiers.extend([uav['name']] * 2)  # Twice per UAV, for start and goal

        positions = np.array(positions)

        if positions.size > 0:
            optics = OPTICS(min_samples=self.min_samples, xi=self.xi, min_cluster_size=self.min_cluster_size)
            optics.fit(positions)
            self.labels = optics.labels_
            
            # Integrate noise with clusters
            self.integrate_noise_with_clusters(positions, self.labels, uav_identifiers)

            clusters = defaultdict(list)
            for idx, label in enumerate(self.labels):
                if label != -1:  # Ignore noise if present
                    uav_name = uav_identifiers[idx]
                    if uav_name not in clusters[label]:
                        clusters[label].append(uav_name)

            # Form initial sub-maps
            for label, uav_names in clusters.items():
                cluster_uavs = [uav for uav in self.uavs if uav['name'] in uav_names]
                all_positions = [pos for uav in cluster_uavs for pos in (uav['start'], uav['goal'])]
                min_x, max_x = np.min([pos[0] for pos in all_positions]), np.max([pos[0] for pos in all_positions])
                min_y, max_y = np.min([pos[1] for pos in all_positions]), np.max([pos[1] for pos in all_positions])

                # Expand bounding boxes by 1 to avoid UAVs on the boundary
                min_x, max_x = max(0, min_x - 1), min(max_x + 1, self.map_size[0] - 1)
                min_y, max_y = max(0, min_y - 1), min(max_y + 1, self.map_size[1] - 1)

                self.sub_maps[label] = {
                    'bounding_box': {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y},
                    'uavs': cluster_uavs
                }

            # Resolve overlapping clusters
            self.sub_maps = self.resolve_overlaps(self.sub_maps)
        else:
            print("Insufficient data for clustering.")
    
    def integrate_noise_with_clusters(self, positions, labels, uav_identifiers):
        noise_indices = np.where(labels == -1)[0]
        if noise_indices.size > 0:
            core_positions = positions[labels != -1]
            core_labels = labels[labels != -1]

            # Calculate the closest cluster for each noise point
            for noise_index in noise_indices:
                distances = np.linalg.norm(core_positions - positions[noise_index], axis=1)
                nearest_cluster_index = np.argmin(distances)
                nearest_cluster_label = core_labels[nearest_cluster_index]
                labels[noise_index] = nearest_cluster_label  # Reassign label

                # Ensure the cluster label exists in self.sub_maps before using it
                if nearest_cluster_label not in self.sub_maps:
                    self.sub_maps[nearest_cluster_label] = {
                        'bounding_box': None,
                        'uavs': []
                    }
                
                # Append UAV to the newly assigned cluster
                uav_name = uav_identifiers[noise_index]
                if uav_name not in self.sub_maps[nearest_cluster_label]['uavs']:
                    self.sub_maps[nearest_cluster_label]['uavs'].append(uav_name)

    def boxes_overlap(self, box1, box2):
        """Check if two bounding boxes overlap."""
        return (box1['min_x'] <= box2['max_x'] and box1['max_x'] >= box2['min_x'] and
                box1['min_y'] <= box2['max_y'] and box1['max_y'] >= box2['min_y'])

    def merge_clusters(self, cluster1, cluster2):
        """Merge two clusters into one, ensuring unique UAVs."""
        # Combine UAV lists and remove duplicates based on UAV names
        combined_uavs = {uav['name']: uav for uav in cluster1['uavs'] + cluster2['uavs']}.values()

        # Calculate the new bounding box to encompass both clusters
        min_x = min(cluster1['bounding_box']['min_x'], cluster2['bounding_box']['min_x'])
        max_x = max(cluster1['bounding_box']['max_x'], cluster2['bounding_box']['max_x'])
        min_y = min(cluster1['bounding_box']['min_y'], cluster2['bounding_box']['min_y'])
        max_y = max(cluster1['bounding_box']['max_y'], cluster2['bounding_box']['max_y'])

        return {
            'bounding_box': {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y},
            'uavs': list(combined_uavs)  # Convert from dict_values to list
        }

    def resolve_overlaps(self, sub_maps):
        """Resolve overlaps among clusters by merging them.""" 
        changed = True
        while changed:
            changed = False
            keys = list(sub_maps.keys())
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    key1, key2 = keys[i], keys[j]
                    if self.boxes_overlap(sub_maps[key1]['bounding_box'], sub_maps[key2]['bounding_box']):
                        sub_maps[key1] = self.merge_clusters(sub_maps[key1], sub_maps[key2])
                        del sub_maps[key2]
                        changed = True
                        break
                if changed:
                    break
        return sub_maps
    
    def get_sub_maps(self):
        """
        Return the calculated sub-maps, each covering the area for its respective cluster of UAVs.
        """
        return self.sub_maps

    def create_map_file(self, cluster_id, cluster_data):
        bounding_box = cluster_data['bounding_box']
        uavs = cluster_data['uavs']
        width = bounding_box['max_x'] - bounding_box['min_x'] + 1
        height = bounding_box['max_y'] - bounding_box['min_y'] + 1

        scen_filename = f"submap_{cluster_id}.scen"
        # Count the number of UAVs
        uav_count = len(uavs)

        # Initialize the grid
        grid = [['.' for _ in range(width)] for _ in range(height)]

        # Place obstacles
        for x, y in self.obstacles:
            if bounding_box['min_x'] <= x <= bounding_box['max_x'] and bounding_box['min_y'] <= y <= bounding_box['max_y']:
                grid[y - bounding_box['min_y']][x - bounding_box['min_x']] = '@'

        map_filename = f"submap_{cluster_id}.map"
        with open(map_filename, 'w') as file:
            file.write("type octile\n")
            file.write(f"height {height}\n")
            file.write(f"width {width}\n")
            file.write("map\n")
            for row in grid:
                file.write(''.join(row) + '\n')

        # Create .scen file
        with open(scen_filename, 'w') as file:
            file.write("version 1\n")
            for idx, uav in enumerate(uavs):
                start_x = uav['start'][0] - bounding_box['min_x']
                start_y = uav['start'][1] - bounding_box['min_y']
                goal_x = uav['goal'][0] - bounding_box['min_x']
                goal_y = uav['goal'][1] - bounding_box['min_y']
                optimal_length = uav.get('optimal_length', -1)
                id = uav.get('id', idx)
                #file.write(f"{id:<4} {map_filename:<16} {width:<4} {height:<4} {start_x:<4} {start_y:<4} {goal_x:<4} {goal_y:<4} {optimal_length:<.8f}\n")
                file.write(f"{id}\t{map_filename}\t{width}\t{height}\t{start_x}\t{start_y}\t{goal_x}\t{goal_y}\t{optimal_length:.8f}\n")

        print(f"Map file {map_filename} created with size {width}x{height}")

        return uav_count

