from flask import Flask, request, render_template, send_from_directory, redirect, url_for
import os
import cv2
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2 import model_zoo

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# Configure Detectron2 model
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml"))
weights_path = "model_final.pth"  # Update with your model weights path if needed
if not os.path.exists(weights_path):
    print(f"Model weights not found at {weights_path}. Please verify the path.")
else:
    cfg.MODEL.WEIGHTS = weights_path

cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7
cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1  # Set number of classes to 1 for a single class (e.g., pothole)

try:
    predictor = DefaultPredictor(cfg)
except Exception as e:
    print(f"Error loading model weights: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    if file.filename == '':
        return "No selected file", 400

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(image_path)

    image = cv2.imread(image_path)

    try:
        outputs = predictor(image)
    except Exception as e:
        return f"Prediction failed: {e}", 500

    # Get prediction boxes, classes, and scores
    boxes = outputs["instances"].pred_boxes.tensor.cpu().numpy().tolist()
    classes = outputs["instances"].pred_classes.cpu().numpy().tolist()
    scores = outputs["instances"].scores.cpu().numpy().tolist()

    # Draw bounding boxes for detected objects
    for box, cls, score in zip(boxes, classes, scores):
        box = [int(coord) for coord in box]
        cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
        cv2.putText(image, f'Class: {cls}, Score: {score:.2f}', 
                   (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    if not os.path.exists(app.config['RESULT_FOLDER']):
        os.makedirs(app.config['RESULT_FOLDER'])

    output_image_path = os.path.join(app.config['RESULT_FOLDER'], f'output_{file.filename}')
    cv2.imwrite(output_image_path, image)

    return render_template('prediction.html', output_image=f'output_{file.filename}')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/results/<filename>')
def result_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
