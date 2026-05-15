"""
Test YOLO detection on video samples.
Simple script to verify YOLO is working correctly.
"""

import cv2
import sys
from pathlib import Path
from ultralytics import YOLO


def test_yolo_on_video(video_path: str, model_path: str = "models/yolov8n.pt") -> None:
    """
    Test YOLO detection on a video file.
    
    Args:
        video_path: Path to video file
        model_path: Path to YOLO model weights
    """
    # Check if video exists
    if not Path(video_path).exists():
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)
    
    print(f"📹 Testing YOLO on video: {video_path}")
    print(f"🤖 Using model: {model_path}")
    
    try:
        # Load YOLO model
        print("\n⏳ Loading YOLO model...")
        model = YOLO(model_path)
        print("✅ YOLO model loaded successfully!")
        
        # Open video
        print(f"\n⏳ Opening video file...")
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"❌ Error: Could not open video file: {video_path}")
            sys.exit(1)
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"✅ Video opened successfully!")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")
        print(f"   Total frames: {frame_count}")
        
        # Process frames
        frame_num = 0
        detections_summary = {}
        
        print(f"\n⏳ Processing frames...")
        
        while cap.isOpened():
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frame_num += 1
            
            # Skip frames for faster processing (every 5th frame)
            if frame_num % 5 != 0:
                continue
            
            # Run YOLO inference
            results = model(frame, verbose=False)
            
            # Extract detections
            if results[0].boxes:
                print(f"\n📊 Frame {frame_num}:")
                
                for box in results[0].boxes:
                    class_id = int(box.cls)
                    confidence = float(box.conf)
                    class_name = results[0].names[class_id]
                    
                    # Track detections
                    if class_name not in detections_summary:
                        detections_summary[class_name] = {"count": 0, "avg_conf": 0}
                    
                    detections_summary[class_name]["count"] += 1
                    detections_summary[class_name]["avg_conf"] += confidence
                    
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    print(f"   - {class_name:15} | Confidence: {confidence:.2f} | Box: ({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})")
            
            # Show progress
            if frame_num % 30 == 0:
                progress = (frame_num / frame_count) * 100
                print(f"   Progress: {progress:.1f}% ({frame_num}/{frame_count} frames processed)")
        
        cap.release()
        
        # Summary
        print(f"\n" + "="*70)
        print("✅ YOLO Detection Summary:")
        print("="*70)
        
        if detections_summary:
            total_detections = sum(d["count"] for d in detections_summary.values())
            print(f"\n📈 Total detections: {total_detections}")
            print(f"\nDetection breakdown:")
            
            for class_name, stats in sorted(detections_summary.items(), key=lambda x: x[1]["count"], reverse=True):
                avg_conf = stats["avg_conf"] / stats["count"]
                print(f"   {class_name:15} | Count: {stats['count']:3d} | Avg Confidence: {avg_conf:.2f}")
        else:
            print("\n⚠️  No detections found in video.")
        
        print("\n" + "="*70)
        print("✅ YOLO test completed successfully!")
        print("="*70)
        
    except ImportError as e:
        print(f"❌ Error: Missing required package - {e}")
        print("   Install with: pip install ultralytics opencv-python")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during YOLO processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Default video path
    video_path = "data/car-detection.mp4"
    
    # Check command line arguments
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    
    # Run test
    test_yolo_on_video(video_path)
