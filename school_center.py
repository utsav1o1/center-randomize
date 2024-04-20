import math
import csv
import random
import argparse
from typing import Dict, List

# Constants
PREF_DISTANCE_THRESHOLD = 2  # Preferred threshold distance in kilometers
ABS_DISTANCE_THRESHOLD = 7  # Absolute threshold distance in kilometers
MIN_STUDENT_IN_CENTER = 10  # Minimum number of students from a school to be assigned to a center under normal circumstances
STRETCH_CAPACITY_FACTOR = 0.02  # How much can center capacity be stretched if need arises
PREF_CUTOFF = -4  # Do not allocate students with preference score less than cutoff

class School:
    def __init__(self, scode, count, name, address, lat, long):
        self.scode = scode
        self.count = int(count)
        self.name = name
        self.address = address
        self.lat = float(lat)
        self.long = float(long)

class Center:
    def __init__(self, cscode, capacity, name, address, lat, long):
        self.cscode = cscode
        self.capacity = int(capacity)
        self.name = name
        self.address = address
        self.lat = float(lat)
        self.long = float(long)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth specified in decimal degrees
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    radius_earth = 6371  # Radius of Earth in kilometers
    distance = radius_earth * c
    return distance

def read_tsv(file_path: str) -> List[Dict[str, str]]:
    data = []
    with open(file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            data.append(dict(row))
    return data

def read_prefs(file_path: str) -> Dict[str, Dict[str, int]]:
    prefs = {}
    with open(file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            if prefs.get(row['scode']):
                if prefs[row['scode']].get(row['cscode']):
                    prefs[row['scode']][row['cscode']] += int(row['pref'])
                else:
                    prefs[row['scode']][row['cscode']] = int(row['pref'])
            else:
                prefs[row['scode']] = {row['cscode']: int(row['pref'])}
    return prefs

def centers_within_distance(school: School, centers: List[Center], distance_threshold: float) -> List[Center]:
    within_distance = []
    nearest_distance = None
    nearest_center = None

    for center in centers:
        distance = haversine_distance(school.lat, school.long, center.lat, center.long)
        if school.scode == center.cscode:
            continue

        if nearest_center is None or distance < nearest_distance:
            nearest_center = center
            nearest_distance = distance

        if distance <= distance_threshold and get_pref(school.scode, center.cscode) > PREF_CUTOFF:
            within_distance.append(center)

    if within_distance:
        return sorted(within_distance, key=lambda x: random.uniform(1, 5) * x.capacity)
    else:
        return [nearest_center]

def get_pref(scode, cscode) -> int:
    if prefs.get(scode):
        return prefs[scode].get(cscode, 0)
    return 0

def allocate(scode:str, cscode:str, count: int):
    if allocations.get(scode) is None:
        allocations[scode] = {cscode: count}
    elif allocations[scode].get(cscode) is None:
        allocations[scode][cscode] = count
    else:
        allocations[scode][cscode] += count

def is_allocated(scode1: str, scode2:str) -> bool:
    if allocations.get(scode1):
        return allocations[scode1].get(scode2) is not None
    return False

def allocate_students_to_centers(schools: List[School], centers: List[Center]):
    global allocations
    allocations = {}
    remaining_students = 0

    with open('school-center-distance.tsv', 'w') as intermediate_file, open(args.output, 'w') as a_file:
        writer = csv.writer(intermediate_file, delimiter="\t")
        writer.writerow(["scode", "s_count", "school_name", "school_lat", "school_long", "cscode", "center_name", "center_address", "center_capacity", "distance_km"])

        allocation_file = csv.writer(a_file, delimiter='\t')
        allocation_file.writerow(["scode", "school", "cscode", "center", "center_address", "allocation", "distance_km"])

        for school in schools:
            centers_for_school = centers_within_distance(school, centers, PREF_DISTANCE_THRESHOLD)
            students_to_allocate = school.count
            per_center = min(students_to_allocate, MIN_STUDENT_IN_CENTER)

            allocated_centers = {}

            for center in centers_for_school:
                writer.writerow([school.scode, school.count, school.name, school.lat, school.long, center.cscode, center.name, center.address, center.capacity, center.distance_km])
                if is_allocated(center.cscode, school.scode):
                    continue
                next_allocation = min(students_to_allocate, per_center, center.capacity)
                if next_allocation > 0:
                    allocate(school.scode, center.cscode, next_allocation)
                    allocation_file.writerow([school.scode, school.name, center.cscode, center.name, center.address, next_allocation, center.distance_km])
                    students_to_allocate -= next_allocation

            if students_to_allocate > 0:
                remaining_students += students_to_allocate
                print(f"{students_to_allocate}/{school.count} left for {school.scode} {school.name} centers: {len(centers_for_school)}")

        print("Remaining capacity at each center (remaining_capacity cscode):")
        remaining_capacity_per_center = {k: v for k, v in centers_remaining_cap.items() if v != 0}
        print(sorted([(v, k) for k, v in remaining_capacity_per_center.items()]))
        print(f"Total remaining capacity across all centers: {sum(remaining_capacity_per_center.values())}")
        print(f"Students not assigned: {remaining_students}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog='center randomizer',
                        description='Assigns centers to exam centers to students')
    parser.add_argument('schools_tsv', default='schools.tsv', help="Tab separated (TSV) file containing school details")
    parser.add_argument('centers_tsv', default='centers.tsv', help="Tab separated (TSV) file containing center details")
    parser.add_argument('prefs_tsv', default='prefs.tsv', help="Tab separated (TSV) file containing preference scores")
    parser.add_argument('-o', '--output', default='school-center.tsv', help='Output file')
    args = parser.parse_args()

    schools_data = read_tsv(args.schools_tsv)
    centers_data = read_tsv(args.centers_tsv)
    prefs = read_prefs(args.prefs_tsv)

    schools = [School(**school) for school in schools_data]
    centers = [Center(**center) for center in centers_data]

    allocate_students_to_centers(schools, centers)
