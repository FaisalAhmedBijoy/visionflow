"""
Debug script to test FileSource directly.
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from visionflow.ingestion.file import FileSource


async def test_file_source() -> None:
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
        print(f"Reading frame {frame_count}...")
        
        # Check if frame is a numpy array (since we changed the return type)
        import numpy as np
        if isinstance(frame, np.ndarray):
            print(f"✅ Success! Frame {frame_count} read successfully")
            print(f"Frame shape: {frame.shape}")
        else:
            print(f"❌ Error: Expected numpy array, got {type(frame)}")
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
