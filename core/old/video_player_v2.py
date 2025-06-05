# core/video_player.py
import vlc
import platform
import logging

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_end_callback=None):
        self.settings_manager = settings_manager
        self.on_end_callback = on_end_callback
        self.instance = vlc.Instance("--no-xlib") # Try with default output first
        self.player = None 
        self.embedded_frame_widget_id = None # Initialized to None
        self.current_media_path = None
        self.current_song_info = None

    def _create_and_setup_player(self):
        logger.debug("== ENTERING _create_and_setup_player ==")
        if self.player:
            logger.debug(f"Releasing previous player instance: {self.player}")
            self.player.stop()
            try:
                old_events = self.player.event_manager()
                if old_events:
                    old_events.event_detach(vlc.EventType.MediaPlayerEndReached)
                    old_events.event_detach(vlc.EventType.MediaPlayerEncounteredError)
                    logger.debug("Detached events from old player.")
            except Exception as e:
                logger.warning(f"Could not detach events from old player: {e}")
            self.player.release()
            self.player = None
            logger.debug("Released previous media player instance.")
        else:
            logger.debug("No previous player instance to release.")

        self.player = self.instance.media_player_new()
        if not self.player:
            logger.error("_create_and_setup_player: FAILED to create new media player instance!")
            return False
        
        logger.debug(f"_create_and_setup_player: New media player instance CREATED: {self.player}")
        events = self.player.event_manager()
        if events:
            events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_media_end)
            events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._handle_media_error)
            logger.debug("_create_and_setup_player: Event handlers ATTACHED to new player.")
        else:
            logger.error("_create_and_setup_player: FAILED to get event manager for new player!")
            return False 
        logger.debug("== EXITING _create_and_setup_player (SUCCESS) ==")
        return True

    def _handle_media_end(self, event):
        logger.info(f"VLC Event: MediaEnded for {self.current_media_path}")
        self.current_media_path = None 
        if self.on_end_callback:
            self.on_end_callback(event)

    def _handle_media_error(self, event):
        media_path_for_log = self.current_media_path or "unknown media (error triggered manually)"
        logger.error(f"VLC Event: MediaPlayerEncounteredError for {media_path_for_log}.")
        self.current_media_path = None 
        if self.on_end_callback:
            self.on_end_callback(event)

    def set_embedding_widget(self, frame_widget): # Called ONCE by PlayerUI
        if frame_widget:
            try:
                widget_id = frame_widget.winfo_id()
                self.embedded_frame_widget_id = widget_id
                logger.info(f"Embedding frame ID SET to: {self.embedded_frame_widget_id} (Type: {type(self.embedded_frame_widget_id)})")
            except tk.TclError as e:
                logger.error(f"Error getting winfo_id for frame_widget in set_embedding_widget: {e}", exc_info=True)
                self.embedded_frame_widget_id = None
        else:
            logger.error("set_embedding_widget called with None frame_widget.")
            self.embedded_frame_widget_id = None

    def _embed_player(self): # Called by play() for EACH new player
        logger.debug(f"_embed_player: Checking conditions. self.player={self.player}, self.embedded_frame_widget_id={self.embedded_frame_widget_id}")
        if not self.player:
            logger.warning("_embed_player: Called but self.player is None. Cannot embed.")
            return False 
        if not self.embedded_frame_widget_id: # This check is critical
            logger.warning(f"_embed_player: No embedded_frame_widget_id is set for player {self.player}. Video will use its own window.")
            return False 

        logger.debug(f"_embed_player: Attempting to embed player {self.player} into frame ID: {self.embedded_frame_widget_id}")
        try:
            if platform.system() == "Linux":
                self.player.set_xwindow(self.embedded_frame_widget_id)
            elif platform.system() == "Windows":
                self.player.set_hwnd(self.embedded_frame_widget_id)
            elif platform.system() == "Darwin":
                self.player.set_hwnd(self.embedded_frame_widget_id)
            logger.info(f"_embed_player: Embedding setup attempted for player {self.player} into frame ID: {self.embedded_frame_widget_id}")
            return True 
        except Exception as e:
            logger.error(f"_embed_player: EXCEPTION during embedding player {self.player}: {e}", exc_info=True)
            return False

    def play(self, video_path, song_info=None):
        logger.info(f"== VideoPlayer.play - Play requested for: {video_path} ==") # Line ~188
        if not video_path:
            logger.error("No video path provided. Aborting play.")
            return

        logger.debug("VideoPlayer.play: Calling _create_and_setup_player()...")
        if not self._create_and_setup_player():
             logger.error("VideoPlayer.play: _create_and_setup_player() FAILED. Aborting play.")
             self._handle_media_error(None) 
             return
        logger.debug(f"VideoPlayer.play: _create_and_setup_player() SUCCEEDED. New player: {self.player}")
        
        logger.debug(f"VideoPlayer.play: Just before calling _embed_player. self.embedded_frame_widget_id = {self.embedded_frame_widget_id} (Type: {type(self.embedded_frame_widget_id)}), self.player = {self.player}") # Line ~204
        
        # Call _embed_player and check its return.
        # The WARNING "No frame widget to embed into..." should come from _embed_player if the ID is None.
        if not self._embed_player(): 
            logger.warning(f"VideoPlayer.play: _embed_player() reported an issue or that no embedding ID was set for {video_path}.")
            # VLC will likely open its own window if _embed_player returned False because ID was None.
            # We proceed to try and play anyway, as the user might still want audio.

        try:
            # ... (rest of the play method as before, e.g., media creation, set_media, player.play() call)
            logger.debug(f"VideoPlayer.play: Creating media for '{video_path}'")
            media = self.instance.media_new(video_path)
            # ... (the rest of the try-except block from previous correct version) ...
            if not media:
                logger.error(f"VideoPlayer.play: self.instance.media_new() FAILED for path: {video_path}. Aborting.")
                self._handle_media_error(None)
                return
            
            self.player.set_media(media)
            media.release() 
            logger.debug(f"VideoPlayer.play: Media set. Calling self.player.play().")

            play_result = self.player.play()
            logger.info(f"VideoPlayer.play: self.player.play() for '{video_path}' returned: {play_result}") # Line ~217 in your log

            if play_result == -1:
                logger.error(f"VideoPlayer.play: self.player.play() FAILED (returned -1) for {video_path}. Aborting.")
                self._handle_media_error(None)
                return
            
            self.current_media_path = video_path
            self.current_song_info = song_info
            logger.info(f"VideoPlayer.play: Playback INITIATED for: {song_info['artist'] if song_info else 'Unknown'} - {song_info['title'] if song_info else video_path}") # Line ~242 in your log

        except Exception as e:
            logger.error(f"VideoPlayer.play: EXCEPTION during play setup for {video_path}: {e}", exc_info=True)
            self.current_media_path = None
            self.current_song_info = None
            self._handle_media_error(None)
        logger.info(f"== VideoPlayer.play - FINISHED for: {video_path} ==")

    def stop(self):
        if self.player:
            logger.info(f"Stop called. Current media: {self.current_media_path}. Player: {self.player}")
            self.player.stop()
        self.current_media_path = None
        self.current_song_info = None

    def pause(self):
        if self.player:
            self.player.pause() # Toggles pause/play

    def set_volume(self, volume): # Volume 0-100
        if self.player:
            # Ensure volume is within VLC's typical effective range (0-200, though 100 is normal max)
            # For safety, clamp to 0-100 if that's what your UI expects.
            safe_volume = max(0, min(int(volume), 200)) # VLC can go higher than 100
            self.player.audio_set_volume(safe_volume)
            logger.debug(f"Volume set to {safe_volume}")

    def get_volume(self):
        return self.player.audio_get_volume() if self.player else 0

    def get_state(self):
        """ Returns the current state of the player (e.g., Playing, Paused, Ended). """
        if self.player: # Check if the player object exists
            return self.player.get_state()
        # If self.player is None (e.g., before first play or after release),
        # return a sensible default state. Ended or Stopped are common.
        return vlc.State.Ended

    def get_current_song_info(self):
        return self.current_song_info

    # release() method should already be there from previous versions
    def release(self):
        logger.info("VideoPlayer.release called for app shutdown.")
        if self.player:
            logger.debug(f"Releasing final player {self.player}. Current state: {self.player.get_state()}")
            self.player.stop()
            try:
                old_events = self.player.event_manager()
                if old_events:
                    old_events.event_detach(vlc.EventType.MediaPlayerEndReached)
                    old_events.event_detach(vlc.EventType.MediaPlayerEncounteredError)
            except Exception as e: logger.warning(f"Exception detaching events on final release: {e}")
            self.player.release()
            self.player = None
            logger.debug("Final media player instance released.")
        if self.instance:
            self.instance.release()
            self.instance = None
            logger.debug("VLC instance released.")
        self.embedded_frame_widget_id = None