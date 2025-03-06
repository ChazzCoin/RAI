# from google.cloud import vision
# import os
# from pdf2image import convert_from_path
#
# client = vision.ImageAnnotatorClient()
# imgdir = '/Users/chazzromeo/Desktop/data/Doc1.pdf'
# texts = []
# pages = convert_from_path(imgdir)
# for idx, page in enumerate(pages):
#     image_path = os.path.join('/Users/chazzromeo/Desktop/data', f"page_{idx + 1}.png")
#     page.save(image_path)
#     with open(image_path, "rb") as image_file:
#         content = image_file.read()
#         image = vision.Image(content=content)
#         response = client.text_detection(image=image)
#         texts.append(response.text_annotations)
#
# print("Texts:")
# for text in texts:
#     print(f'\n"{text}"')
#     # vertices = [f"({vertex.x},{vertex.y})" for vertex in te.bounding_poly.vertices]
#     # print("bounds: {}".format(",".join(vertices)))