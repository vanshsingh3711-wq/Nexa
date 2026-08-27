import time
from actions.media.media_actions import toggle_play_pause

def run_test():
    print("=== Media Action Test ===")
    print("Make sure you have a media player (like Spotify, YouTube, or Apple Music) open in the background.")
    
    while True:
        user_input = input("\nPress [Enter] to simulate the 'Open Palm' gesture (or type 'q' to quit): ")
        
        if user_input.lower() == 'q':
            print("Exiting test...")
            break
            
        print("Toggling Play/Pause...")
        success = toggle_play_pause()
        
        if success:
            print("Action triggered successfully! Did your media play/pause?")
        else:
            print("Failed to trigger the action.")

if __name__ == "__main__":
    run_test()
