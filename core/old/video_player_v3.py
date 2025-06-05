# core/video_player.py
import vlc
import platform
import logging
import tkinter as tk # For tk.TclError in set_embedding_widget

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_end_callback=None):
        self.settings_manager = settings_manager
        self.on_end_callback = on_end_callback
        logger.info("VideoPlayer: Initializing VLC instance with --avcodec-hw=none AND --vout=wingdi")
        #self.instance = vlc.Instance("--no-xlib --avcodec-hw=none --vout=wingdi")
        self.instance = vlc.Instance("--no-xlib --avcodec-hw=none")
        self.player = None 
        self.embedded_frame_widget_id = None
        self.current_media_path = None
        self.current_song_info = None

# core/video_player.py

    def _create_and_setup_player(self):
        logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.1: ENTERED method.")

        if self.player: # If there's an old player object
            logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.2: Old player exists ({self.player}). Will attempt to create new, orphaning old.")
            # We will not interact with old_player directly here to avoid hangs.
            # We rely on MediaPlayerEndReached having been fired and self.player being overwritten.
            # Python's garbage collector and VLC's internal management should eventually clean it up
            # once our self.player reference is reassigned. This is a risk for resource leaks
            # if VLC doesn't clean up well after errors, but we're trying to avoid the hang.
            # Detaching events MIGHT still be safe and good.
            try:
                logger.debug(f"Attempting to detach events from old player: {self.player}")
                old_events = self.player.event_manager()
                if old_events:
                    old_events.event_detach(vlc.EventType.MediaPlayerEndReached)
                    old_events.event_detach(vlc.EventType.MediaPlayerEncounteredError)
                    logger.debug("Detached events from old player.")
            except Exception as e_ev:
                logger.error(f"EXCEPTION while detaching events from old player: {e_ev}", exc_info=True)
            
            # We are deliberately NOT calling self.player.stop() or self.player.release() here
            # to see if that avoids the hang.
            self.player = None # Nullify our reference.
            logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.6A: Old self.player reference nullified.")
        else:
            logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.2A: No old player to release/nullify.")

        logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.7: Attempting self.instance.media_player_new(). Instance: {self.instance}")
        try:
            new_player_candidate = self.instance.media_player_new() # Create the new one
            logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.8: media_player_new() returned: {new_player_candidate}")
        except Exception as e:
            logger.error(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.E2: EXCEPTION during media_player_new(): {e}", exc_info=True)
            new_player_candidate = None
            
        if not new_player_candidate:
            logger.error("VideoPlayer._create_and_setup_player - CHECKPOINT 4.9: FAILED to create new player. Returning False.")
            return False
        
        self.player = new_player_candidate # Assign the NEW player to self.player
        logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.10: New player ASSIGNED: {self.player}. Setting up events.")
        
        # ... (rest of event setup as before) ...
        try:
            events = self.player.event_manager()
            if events:
                events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_media_end)
                events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._handle_media_error)
                logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.11: Events ATTACHED.")
            else: # Should not happen
                logger.error("VideoPlayer._create_and_setup_player - CHECKPOINT 4.12: FAILED to get event manager!")
                if self.player: self.player.release()
                self.player = None
                return False
        except Exception as e:
            logger.error(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.E3: EXCEPTION during event setup: {e}", exc_info=True)
            if self.player: self.player.release()
            self.player = None
            return False

        logger.info("== VideoPlayer._create_and_setup_player - CHECKPOINT 4.13: EXITING (SUCCESS) ==")
        return True

    def _handle_media_end(self, event):
        logger.info(f"VLC Event: MediaEnded for {self.current_media_path}")
        self.current_media_path = None 
        if self.on_end_callback:
            self.on_end_callback(event)

    def _handle_media_error(self, event):
        media_path_for_log = self.current_media_path or "unknown media (triggered manually)"
        logger.error(f"VLC Event: MediaPlayerEncounteredError for {media_path_for_log}.")
        self.current_media_path = None 
        if self.on_end_callback:
            self.on_end_callback(event)

    def set_embedding_widget(self, frame_widget):
        if frame_widget:
            try:
                widget_id = frame_widget.winfo_id()
                self.embedded_frame_widget_id = widget_id
                logger.info(f"Embedding frame ID SET to: {self.embedded_frame_widget_id} (Type: {type(self.embedded_frame_widget_id)})")
            except tk.TclError as e:
                logger.error(f"Error getting winfo_id for frame_widget: {e}", exc_info=True)
                self.embedded_frame_widget_id = None
        else:
            logger.error("set_embedding_widget called with None frame_widget.")
            self.embedded_frame_widget_id = None

    def _embed_player(self): # Called by play() for EACH new player
        logger.info(f"== VideoPlayer._embed_player: ENTERED. Player: {self.player}. Stored Frame ID: {self.embedded_frame_widget_id} (Type: {type(self.embedded_frame_widget_id)}) ==")
        
        if not self.player:
            logger.warning("_embed_player: self.player is None. Cannot embed.")
            return False 
        if not self.embedded_frame_widget_id: # This check is critical
            logger.warning(f"_embed_player: self.embedded_frame_widget_id is None/Falsy. Player {self.player} will use its own window.")
            return False 

        logger.debug(f"_embed_player: Attempting to embed player {self.player} into frame ID: {self.embedded_frame_widget_id}")
        try:
            # It's CRITICAL that self.player here is the NEWLY created player instance
            if platform.system() == "Linux":
                self.player.set_xwindow(self.embedded_frame_widget_id)
            elif platform.system() == "Windows":
                self.player.set_hwnd(self.embedded_frame_widget_id)
            elif platform.system() == "Darwin":
                self.player.set_hwnd(self.embedded_frame_widget_id)
            logger.info(f"_embed_player: Embedding setup SUCCESSFUL for player {self.player} into frame ID: {self.embedded_frame_widget_id}")
            return True 
        except Exception as e:
            logger.error(f"_embed_player: EXCEPTION during embedding player {self.player} into ID {self.embedded_frame_widget_id}: {e}", exc_info=True)
            return False

    def play(self, video_path, song_info=None):
        # Using the heavily logged version from previous successful first play
        logger.info(f"== VideoPlayer.play - ATTEMPTING. Path: '{video_path}', Title: '{song_info.get('title', 'N/A') if song_info else 'N/A'}' ==")
        try:
            logger.info("VideoPlayer.play - CHECKPOINT 1: Inside try block, before path check.")
            if not video_path:
                logger.error(f"VideoPlayer.play - CHECKPOINT 2: video_path IS FALSY ('{video_path}'). Aborting.")
                if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
                return
            logger.info(f"VideoPlayer.play - CHECKPOINT 3: video_path ('{video_path}') is VALID. Proceeding...")
            logger.info("VideoPlayer.play - CHECKPOINT 4: Calling _create_and_setup_player()...")
            if not self._create_and_setup_player():
                logger.error("VideoPlayer.play - CHECKPOINT 5: _create_and_setup_player() FAILED. Aborting.")
                if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
                return
            logger.info(f"VideoPlayer.play - CHECKPOINT 6: _create_and_setup_player() SUCCEEDED. Player: {self.player}")
            logger.info(f"VideoPlayer.play - CHECKPOINT 7: Before _embed_player. ID: {self.embedded_frame_widget_id}")
            if not self._embed_player():
                logger.warning(f"VideoPlayer.play - CHECKPOINT 8: _embed_player() FAILED or reported issue for {video_path}.")
            else:
                logger.info(f"VideoPlayer.play - CHECKPOINT 8: _embed_player() SUCCEEDED for {video_path}.")
            logger.info("VideoPlayer.play - CHECKPOINT 9: Creating media object.")
            media = self.instance.media_new(video_path)
            if not media:
                logger.error(f"VideoPlayer.play - CHECKPOINT 10: media_new() FAILED for {video_path}.")
                if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
                return
            logger.info("VideoPlayer.play - CHECKPOINT 11: Setting media.")
            self.player.set_media(media)
            media.release()
            logger.info("VideoPlayer.play - CHECKPOINT 12: Calling actual player.play().")
            play_result = self.player.play()
            logger.info(f"VideoPlayer.play - CHECKPOINT 13: player.play() returned {play_result} for {video_path}.")
            if play_result == -1:
                logger.error(f"VideoPlayer.play - CHECKPOINT 14: player.play() returned -1 (FAILED) for {video_path}.")
                if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
                return
            self.current_media_path = video_path
            self.current_song_info = song_info
            logger.info(f"VideoPlayer.play - CHECKPOINT 15: Playback INITIATED for: {song_info.get('title', 'N/A') if song_info else video_path}")
        except Exception as e:
            logger.error(f"VideoPlayer.play - CHECKPOINT E: UNHANDLED EXCEPTION in play method: {e}", exc_info=True)
            self.current_media_path = None
            self.current_song_info = None
            if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
        logger.info(f"== VideoPlayer.play - ATTEMPT FINISHED for: {video_path} ==")

    # --- ADD THESE METHODS BACK ---
    def stop(self):
        if self.player:
            logger.info(f"Stop called. Current media: {self.current_media_path}. Player: {self.player}")
            try:
                self.player.stop()
            except Exception as e:
                logger.error(f"Exception during player.stop(): {e}", exc_info=True)
        self.current_media_path = None
        self.current_song_info = None

    def pause(self):
        if self.player:
            try:
                self.player.pause() # Toggles pause/play
            except Exception as e:
                logger.error(f"Exception during player.pause(): {e}", exc_info=True)


    def set_volume(self, volume): # Volume 0-100
        if self.player:
            try:
                safe_volume = max(0, min(int(volume), 200)) 
                self.player.audio_set_volume(safe_volume)
                logger.debug(f"Volume set to {safe_volume}")
            except Exception as e:
                logger.error(f"Exception during player.audio_set_volume(): {e}", exc_info=True)


    def get_volume(self):
        if self.player:
            try:
                return self.player.audio_get_volume()
            except Exception as e:
                logger.error(f"Exception during player.audio_get_volume(): {e}", exc_info=True)
                return 0 # Default or error value
        return 0

    def get_state(self):
        if self.player:
            try:
                return self.player.get_state()
            except Exception as e: # Catch potential errors if player is in a bad state
                logger.error(f"Exception getting player state: {e}", exc_info=True)
                return vlc.State.Error # Indicate an error state
        return vlc.State.Ended 

    def get_current_song_info(self):
        return self.current_song_info
    # --- END OF ADDED METHODS ---

    def release(self):
        logger.info("VideoPlayer.release called for app shutdown.")
        if self.player: # Release the current player if it exists
            logger.debug(f"Releasing final player {self.player} (State: {self.get_state()})")
            try: self.player.stop()
            except Exception as e: logger.warning(f"Exception stopping player on release: {e}", exc_info=True)
            try:
                evts = self.player.event_manager()
                if evts:
                    evts.event_detach(vlc.EventType.MediaPlayerEndReached)
                    evts.event_detach(vlc.EventType.MediaPlayerEncounteredError)
                    logger.debug("Detached events from final player on release.")
            except Exception as e: logger.warning(f"Exception detaching events on release: {e}", exc_info=True)
            try: self.player.release()
            except Exception as e: logger.warning(f"Exception releasing player on release: {e}", exc_info=True)
            self.player = None # Crucial
            logger.debug("Final media player instance released.")
        
        if self.instance: # Release the single VLC instance
            logger.debug(f"Releasing VLC instance: {self.instance}")
            try:
                self.instance.release()
                logger.info("VLC instance released successfully.")
            except Exception as e:
                logger.error(f"EXCEPTION releasing VLC instance: {e}", exc_info=True)
            self.instance = None # Crucial
        
        self.embedded_frame_widget_id = None