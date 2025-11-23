from update_yolo_class import YoloClass

VIDEO = r"C:\Users\theba\PycharmProjects\detectedCar\demo\6011568_Car_Vehicle_3840x2160.mp4"

yolo = YoloClass(
    source=VIDEO,
    camera_id="1",
    skip_frames=5,
    resize=(1280, 720),
    model_path="yolo11n.pt"    # модель в корне проекта
)

yolo.run()
