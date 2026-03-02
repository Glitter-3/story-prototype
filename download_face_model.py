"""
下载 OpenCV DNN 人脸检测模型文件
运行一次即可：python download_face_model.py
"""
import urllib.request
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

FILES = {
    'deploy.prototxt': 'https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt',
    'res10_300x300_ssd_iter_140000.caffemodel': 'https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel',
}

for filename, url in FILES.items():
    dest = os.path.join(MODEL_DIR, filename)
    if os.path.exists(dest):
        print(f'已存在，跳过: {filename}')
        continue
    print(f'正在下载 {filename} ...')
    urllib.request.urlretrieve(url, dest)
    print(f'下载完成: {dest}')

print('全部完成！')
