import json
from pathlib import Path
from typing import Set, Tuple

class FrameHistory:
    """
    Manages the history of used frames, persisting it between executions.
    Automatically clears history when reaching 1000 frames.
    """
    MAX_FRAMES = 5000

    def __init__(self, history_file: str = "frame_history.json"):
        self.history_file = Path.cwd() / "temp" / history_file
        self.used_frames: Set[Tuple[int, int]] = set()
        
        # Create temp directory if it doesn't exist
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_history()

    def _load_history(self) -> None:
        """
        Load the frame history from the JSON file.
        Creates the file and directory if they don't exist.
        """
        # Create the file if it doesn't exist
        self.history_file.touch(exist_ok=True)
        
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    # Convert the list of lists back to set of tuples
                    self.used_frames = {(item[0], item[1]) for item in data}
            except json.JSONDecodeError:
                self.used_frames = set()
        else:
            self.used_frames = set()
            self._save_history()

    def _save_history(self) -> None:
        """
        Save the current frame history to the JSON file.
        Formats the output with indentation and line breaks for better readability.
        """
        # Convert set of tuples to list of lists for JSON serialization
        data = [list(item) for item in self.used_frames]
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=4)

    def add_frame(self, frame_number: int, episode_number: int) -> None:
        """
        Add a frame to the history and save it.
        If the history reaches MAX_FRAMES, it will be automatically cleared.
        
        Args:
            frame_number (int): The frame number
            episode_number (int): The episode number
        """
        self.used_frames.add((episode_number, frame_number))
        
        # Check if we need to clear the history
        if len(self.used_frames) >= self.MAX_FRAMES:
            self.clear_history()
        else:
            self._save_history()

    def is_frame_used(self, episode_number: int, frame_number: int) -> bool:
        """
        Check if a frame has been used before.
        
        Args:
            frame_number (int): The frame number to check
            episode_number (int): The episode number to check
            
        Returns:
            bool: True if the frame has been used, False otherwise
        """
        return (episode_number, frame_number) in self.used_frames

    def clear_history(self) -> None:
        """
        Clear the frame history and save the empty state.
        """
        self.used_frames.clear()
        self._save_history()

    def get_used_frames_count(self) -> int:
        """
        Get the total number of frames that have been used.
        
        Returns:
            int: The number of used frames
        """
        return len(self.used_frames) 