# import csv
# import json
#
# def csv_to_json(csv_file_path, json_file_path):
#     data = []
#
#     with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
#         csv_reader = csv.DictReader(csv_file)
#         for row in csv_reader:
#             data.append(row)
#
#     with open(json_file_path, mode='w', encoding='utf-8') as json_file:
#         json.dump(data, json_file, indent=4)
#
#     print(f"CSV data successfully converted to JSON and saved to {json_file_path}")
#
#
# if __name__ == "__main__":
#     csv_to_json("/Users/chazzromeo/Desktop/radiology_detail.csv", "/Users/chazzromeo/Desktop/radiology_detail.json")
