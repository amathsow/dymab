from sklearn.cluster import OPTICS
import numpy as np
from collections import defaultdict

class UAVClusterManager:
    def __init__(self, uavs, map_size, obstacles, min_samples=2, xi=0.01, min_cluster_size=0.1):
        """
        Initialize the UAVClusterManager with a list of UAVs, each having a 'name', 'start', and 'goal' position,
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
        uav_identifiers = []

        # Collect positions and corresponding UAV identifiers
        for uav in self.uavs:
            positions.extend([uav['start'], uav['goal']])
            uav_identifiers.extend([uav['name']] * 2)

        positions = np.array(positions)

        if positions.size > 0:
            # Use OPTICS to cluster the positions
            print("OPTCIS clustering")
            optics = OPTICS(min_samples=self.min_samples, xi=self.xi, min_cluster_size=self.min_cluster_size)
            self.labels = optics.fit_predict(positions)
            print(set(self.labels))
            
            # Integrate noise UAVs with the nearest clusters
            self._integrate_noise_with_clusters(positions, self.labels, uav_identifiers)

            clusters = defaultdict(list)
            for idx, label in enumerate(self.labels):
                if label != -1:  # Exclude noise UAVs
                    uav_name = uav_identifiers[idx]
                    if uav_name not in clusters[label]:
                        clusters[label].append(uav_name)

            # Form sub-maps for each cluster
            for label, uav_names in clusters.items():
                cluster_uavs = [uav for uav in self.uavs if uav['name'] in uav_names]
                all_positions = [pos for uav in cluster_uavs for pos in (uav['start'], uav['goal'])]
                min_x, max_x = np.min([pos[0] for pos in all_positions]), np.max([pos[0] for pos in all_positions])
                min_y, max_y = np.min([pos[1] for pos in all_positions]), np.max([pos[1] for pos in all_positions])

                # Adjust bounding box to avoid UAVs on the boundary
                min_x, max_x = max(0, min_x - 1), min(max_x + 1, self.map_size[0] - 1)
                min_y, max_y = max(0, min_y - 1), min(max_y + 1, self.map_size[1] - 1)

                self.sub_maps[label] = {
                    'bounding_box': {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y},
                    'uavs': cluster_uavs
                }

            # Resolve overlaps between sub-maps 
            self.sub_maps = self.resolve_overlaps_bbox(self.sub_maps)
        else:
            print("Insufficient data for clustering.")

    def _integrate_noise_with_clusters(self, positions, labels, uav_identifiers):
        """Reassign noise UAVs to the nearest cluster."""
        noise_indices = np.where(labels == -1)[0]
        if noise_indices.size > 0:
            core_positions = positions[labels != -1]
            core_labels = labels[labels != -1]

            for noise_index in noise_indices:
                distances = np.linalg.norm(core_positions - positions[noise_index], axis=1)
                nearest_cluster_index = np.argmin(distances)
                nearest_cluster_label = core_labels[nearest_cluster_index]
                labels[noise_index] = nearest_cluster_label  # Reassign the noise UAV to the nearest cluster

    def resolve_overlaps_bbox(self, sub_maps):
        """Resolve overlaps among clusters """
        keys = list(sub_maps.keys())
        to_remove = []  # List to collect keys for removal

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                key1, key2 = keys[i], keys[j]
                if key1 in sub_maps and key2 in sub_maps and self.boxes_overlap(
                        sub_maps[key1]['bounding_box'], sub_maps[key2]['bounding_box']):
                    
                    # Determine overlapping UAVs
                    uavs_key1 = {uav['name'] for uav in sub_maps[key1]['uavs']}
                    uavs_key2 = {uav['name'] for uav in sub_maps[key2]['uavs']}
                    overlapping_uavs = uavs_key1.intersection(uavs_key2)

                    # Remove overlapping UAVs from the larger cluster (key1)
                    sub_maps[key1]['uavs'] = [uav for uav in sub_maps[key1]['uavs'] if uav['name'] not in overlapping_uavs]

                    # Recalculate bounding box for the larger cluster (key1)
                    if sub_maps[key1]['uavs']:
                        all_positions_key1 = [pos for uav in sub_maps[key1]['uavs'] for pos in (uav['start'], uav['goal'])]
                        min_x_key1, max_x_key1 = np.min([pos[0] for pos in all_positions_key1]), np.max([pos[0] for pos in all_positions_key1])
                        min_y_key1, max_y_key1 = np.min([pos[1] for pos in all_positions_key1]), np.max([pos[1] for pos in all_positions_key1])

                        min_x_key1, max_x_key1 = max(0, min_x_key1 - 1), min(max_x_key1 + 1, self.map_size[0] - 1)
                        min_y_key1, max_y_key1 = max(0, min_y_key1 - 1), min(max_y_key1 + 1, self.map_size[1] - 1)

                        sub_maps[key1]['bounding_box'] = {'min_x': min_x_key1, 'min_y': min_y_key1, 'max_x': max_x_key1, 'max_y': max_y_key1}
                    else:
                        # If the cluster is empty after removal, mark for removal
                        to_remove.append(key1)

        # Remove empty clusters
        for key in to_remove:
            if key in sub_maps:
                del sub_maps[key]

        return sub_maps

    def boxes_overlap(self, box1, box2):
        """Check if two bounding boxes overlap."""
        return (box1['min_x'] < box2['max_x'] and box1['max_x'] > box2['min_x'] and
                box1['min_y'] < box2['max_y'] and box1['max_y'] > box2['min_y'])

    def get_sub_maps(self):
        """Return the calculated sub-maps."""
        return self.sub_maps

    def create_map_file(self, cluster_id, cluster_data):
        bounding_box = cluster_data['bounding_box']
        uavs = cluster_data['uavs']
        width = bounding_box['max_x'] - bounding_box['min_x'] + 1
        height = bounding_box['max_y'] - bounding_box['min_y'] + 1

        scen_filename = f"submap_{cluster_id}.scen"
        uav_count = len(uavs)
        grid = [['.' for _ in range(width)] for _ in range(height)]

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

        with open(scen_filename, 'w') as file:
            file.write("version 1\n")
            for idx, uav in enumerate(uavs):
                start_x = uav['start'][0] - bounding_box['min_x']
                start_y = uav['start'][1] - bounding_box['min_y']
                goal_x = uav['goal'][0] - bounding_box['min_x']
                goal_y = uav['goal'][1] - bounding_box['min_y']
                optimal_length = uav.get('optimal_length', -1)
                id = uav.get('id', idx)
                file.write(f"{id}\t{map_filename}\t{width}\t{height}\t{start_x}\t{start_y}\t{goal_x}\t{goal_y}\t{optimal_length:.8f}\n")

        print(f"Map file {map_filename} created with size {width}x{height}")

        return uav_count
