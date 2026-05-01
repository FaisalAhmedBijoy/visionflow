"""
Debug script to test FileSource directly.
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from visionflow.ingestion import FileSource


async def test_file_source():
    """Test FileSource directly."""
    video_path = "data/car-detection.mp4"
    
    print(f"\n📁 Testing FileSource with: {video_path}")
    print(f"✅ File exists: {Path(video_path).exists()}")
    
    # Create source
    source = FileSource(video_path, source_id="test_video", fps=10)
    
    try:
        # Start source
        print("\n⏳ Starting source...")
        await source.start()
        print("✅ Source started successfully!")
        
        # Read first frame
        print("\n⏳ Reading first frame...")
        frame = await source.read_frame()
        
        if frame is not None:
            print(f"✅ Frame read successfully!")
            print(f"   Shape: {frame.shape}")
            print(f"   Type: {type(frame)}")
        else:
            print("❌ Frame is None!")
        
        # Read a few more frames
        print("\n⏳ Reading 10 more frames...")
        for i in range(10):
            frame = await source.read_frame()
            if frame is None:
                print(f"   Frame {i+1}: None (end of file?)")
                break
            else:
                print(f"   Frame {i+1}: ✅ shape={frame.shape}")
        
        # Stop source
        print("\n⏳ Stopping source...")
        await source.stop()
        print("✅ Source stopped successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_file_source())
