# Parse outputs from unitstacks.py for only specific state
import re

def filter_unitstacks_by_prov(input_file, output_file, prov_ids):
    """
    Filter unitstack entries by province IDs and write to output file.
    
    Args:
        input_file (str): Path to the input unitstacks file
        output_file (str): Path to the output file
        province_ids (list): List of province IDs to filter for
    """
    # Convert province IDs to a set for faster lookup
    target_provinces = set(map(int, prov_ids))

    filtered_entries = []

    try:
        # Open the unitstacks file generated
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Parse every line, stripping whitespace
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('//'):
                    continue

                # Split based on semicolon
                parts = line.split(';')
                # Ensure the line is still valid
                if len(parts) >= 2:
                    # If the province ID is within the filter, add it to the list
                    try:
                        province_id = int(parts[0])
                        if province_id in target_provinces:
                            filtered_entries.append(line)
                    except ValueError:
                        continue

        # Write the filtered entries to the output file
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in filtered_entries:
                f.write(entry + '\n')
        
        print(f"Filtered {len(filtered_entries)} entries for {len(target_provinces)} provinces")
        print(f"Output written to {output_file}")
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # List of province IDs to filter for
    # This base is from 55-Nassau, change as needed
    filtered_provinces = [
        564, 589, 3397, 3524, 3574, 6444, 6488, 6549, 9486, 9524,
        9547, 11445, 11533, 11560, 13402, 13403, 13404, 13405, 13406, 13407,
        13408, 13409, 13410, 13411, 13412, 13413, 13414, 13415, 13416, 13417,
        13418, 13419, 13420, 13421, 13422, 13423, 13424, 13425, 13426, 13427,
        13428, 13429, 13430, 13431, 13432, 13433, 13434, 13435, 13436, 13437,
        13438, 13439, 13440, 13441, 13442, 13443, 13444, 13445, 13446, 13447,
        13448, 13449, 13450, 13451, 13452, 13453, 13454, 13455, 13456, 13457,
        13458, 13459, 13460, 13461, 13462, 13463, 13464, 13465, 13466, 13467,
        13468, 13469, 13470, 13471, 13472, 13473, 13474, 13475, 13476, 13477,
        13478, 13479
    ]

    # Change based on what your output file in unitstacks.py was
    input_file = "output_new.txt"
    output_file = "filtered_unitstacks.txt"

    filter_unitstacks_by_prov(input_file, output_file, filtered_provinces)
