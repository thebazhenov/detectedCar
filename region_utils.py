# roi_rectangle_selector.py
# Кликаешь мышкой → получаешь сразу (x1, y1, x2, y2) = (..., ..., ..., ...)

import cv2
import numpy as np
import matplotlib.pyplot as plt

points = []

def on_click(event):
    if event.button == 1 and event.inaxes:  # левая кнопка
        x, y = int(event.xdata), int(event.ydata)
        points.append([x, y])
        plt.plot(x, y, 'ro', markersize=10)
        plt.gcf().canvas.draw()
        print(f"Точка {len(points)}: [{x}, {y}]")

def select_roi_and_get_rectangle(video_source=0):
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        raise ValueError("Не могу открыть источник видео")

    # Берём кадр из середины видео/потока
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Не удалось прочитать кадр")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    plt.figure(figsize=(16, 9))
    plt.imshow(frame_rgb)
    plt.title("КЛИКАЙ по углам региона (по часовой стрелке)\nЗакрой окно, когда закончишь", fontsize=16)
    plt.axis('off')

    plt.gcf().canvas.mpl_connect('button_press_event', on_click)
    plt.show()

    if len(points) < 3:
        print("Ошибка: нужно минимум 3 точки!")
        return None

    # Считаем bounding box
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]

    x1 = min(x_coords)
    y1 = min(y_coords)
    x2 = max(x_coords)
    y2 = max(y_coords)

    # Красивый вывод — копируй-вставляй сразу в код!
    print("\n" + "="*60)
    print("ГОТОВЫЙ ПРЯМОУГОЛЬНИК ДЛЯ ТВОЕГО ROI:")
    print(f"(x1, y1, x2, y2) = ({x1}, {y1}, {x2}, {y2})")
    print("\nСкопируй эту строку в свой код:")
    print(f"roi_rect = ({x1}, {y1}, {x2}, {y2})")
    print("="*60 + "\n")

    # Дополнительно рисуем прямоугольник на кадре (чтобы ты увидел, что всё ок)
    result = frame.copy()
    cv2.rectangle(result, (x1, y1), (x2, y2), (0, 255, 0), 4)
    cv2.putText(result, f"ROI: ({x1},{y1}) - ({x2},{y2})", (x1, y1-15),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 3)

    cv2.imshow("Твой выбранный прямоугольник", result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return (x1, y1, x2, y2)

# Запуск
if __name__ == "__main__":
    # Укажи 0 для веб-камеры, или путь к видео/RTSP
    roi = select_roi_and_get_rectangle(video_source="test.mov")  # или 0