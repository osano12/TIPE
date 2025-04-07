import cv2
import time

def test_camera():
    print("Test de la caméra...")
    
    # Essai avec différents indices
    for i in [0, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 31]:
        print(f"\nEssai avec la caméra {i}")
        cap = cv2.VideoCapture(i)
        
        if not cap.isOpened():
            print(f"Caméra {i} non accessible")
            continue
            
        print(f"Caméra {i} ouverte")
        print(f"Propriétés de la caméra {i}:")
        print(f"- Largeur: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
        print(f"- Hauteur: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        
        # Tentative de capture
        ret, frame = cap.read()
        if ret:
            print(f"Capture réussie avec la caméra {i}")
            cv2.imwrite(f"test_camera_{i}.jpg", frame)
        else:
            print(f"Échec de capture avec la caméra {i}")
            
        cap.release()
        time.sleep(1)

if __name__ == "__main__":
    test_camera() 