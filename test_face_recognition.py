import cv2
import numpy as np
import sys

def test_gpu():
    """Test if GPU is available"""
    print("=" * 60)
    print("Testing GPU Availability")
    print("=" * 60)
    
    try:
        import onnxruntime as ort
        print(f"\n✓ ONNXRuntime version: {ort.__version__}")
        
        providers = ort.get_available_providers()
        print(f"\nAvailable providers: {', '.join(providers)}")
        
        if 'CUDAExecutionProvider' in providers:
            print("\n✅ GPU (CUDA) is available!")
            print("   Face recognition will use GPU acceleration")
            return True
        else:
            print("\n⚠️  GPU (CUDA) not available")
            print("   Face recognition will use CPU")
            print("\nTo enable GPU:")
            print("1. Install CUDA Toolkit 11.8+")
            print("2. Install cuDNN 8.6+")
            print("3. Run: pip install onnxruntime-gpu")
            return False
    except ImportError:
        print("\n❌ ONNXRuntime not installed")
        print("Run: pip install onnxruntime-gpu")
        return False

def test_insightface():
    """Test InsightFace installation"""
    print("\n" + "=" * 60)
    print("Testing InsightFace Installation")
    print("=" * 60)
    
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        print(f"\n✓ InsightFace version: {insightface.__version__}")
        
        # Initialize face analysis
        print("\nInitializing Face Analysis...")
        app = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        print("✅ InsightFace initialized successfully!")
        return app
        
    except ImportError:
        print("\n❌ InsightFace not installed")
        print("Run: pip install insightface")
        return None
    except Exception as e:
        print(f"\n❌ Error initializing InsightFace: {e}")
        return None

def test_camera():
    """Test camera availability"""
    print("\n" + "=" * 60)
    print("Testing Camera")
    print("=" * 60)
    
    try:
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("\n❌ Camera not accessible")
            print("\nTroubleshooting:")
            print("1. Check if camera is connected")
            print("2. Close other applications using the camera")
            print("3. Check camera permissions")
            return None
        
        ret, frame = cap.read()
        if ret:
            print(f"\n✅ Camera working!")
            print(f"   Resolution: {frame.shape[1]}x{frame.shape[0]}")
            cap.release()
            return True
        else:
            print("\n❌ Could not read from camera")
            cap.release()
            return None
            
    except Exception as e:
        print(f"\n❌ Camera error: {e}")
        return None

def test_face_detection(app):
    """Test face detection with live camera"""
    print("\n" + "=" * 60)
    print("Testing Face Detection (Live)")
    print("=" * 60)
    print("\nInstructions:")
    print("- Position your face in front of the camera")
    print("- Press 'q' to quit")
    print("- Press 's' to capture and test recognition")
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("\n❌ Cannot access camera")
        return
    
    print("\n✓ Camera opened. Starting detection...")
    
    captured_embeddings = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect faces
        faces = app.get(frame)
        
        # Draw rectangles around faces
        for face in faces:
            bbox = face.bbox.astype(int)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            
            # Display confidence
            cv2.putText(frame, f"Conf: {face.det_score:.2f}", 
                       (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (0, 255, 0), 2)
        
        # Display number of faces
        cv2.putText(frame, f"Faces: {len(faces)}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display instructions
        cv2.putText(frame, "Press 'q' to quit, 's' to capture", (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow('Face Detection Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('s') and len(faces) == 1:
            # Capture embedding
            captured_embeddings.append(faces[0].embedding)
            print(f"\n✓ Captured face #{len(captured_embeddings)}")
            print(f"  Embedding shape: {faces[0].embedding.shape}")
            print(f"  Detection confidence: {faces[0].det_score:.4f}")
            
            if len(captured_embeddings) >= 2:
                # Compare embeddings
                emb1 = captured_embeddings[-2]
                emb2 = captured_embeddings[-1]
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                print(f"\n  Similarity with previous capture: {similarity:.4f}")
                print(f"  {'✅ MATCH' if similarity > 0.4 else '❌ NO MATCH'} (threshold: 0.4)")
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print(f"Total faces captured: {len(captured_embeddings)}")
    print("=" * 60)

def run_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Face Recognition System Test Suite" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Test GPU
    has_gpu = test_gpu()
    
    # Test InsightFace
    app = test_insightface()
    
    if app is None:
        print("\n❌ Cannot proceed without InsightFace")
        return False
    
    # Test Camera
    has_camera = test_camera()
    
    if not has_camera:
        print("\n❌ Cannot proceed without camera")
        return False
    
    # Test face detection
    print("\n")
    response = input("Do you want to test live face detection? (y/n): ")
    if response.lower() == 'y':
        test_face_detection(app)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"GPU Available:        {'✅ Yes' if has_gpu else '⚠️  No (CPU mode)'}")
    print(f"InsightFace:          {'✅ Working' if app else '❌ Failed'}")
    print(f"Camera:               {'✅ Working' if has_camera else '❌ Failed'}")
    print("=" * 60)
    
    if app and has_camera:
        print("\n✅ All systems ready! You can start the application.")
        print("\nRun: python app.py")
        return True
    else:
        print("\n⚠️  Some components are not working properly.")
        print("Please fix the issues before running the application.")
        return False

if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)