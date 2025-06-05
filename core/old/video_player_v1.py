#core/video_player.py
import vlc
import platform # To get OS type for VLC embedding
import logging

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_end_callback=None):
        self.settings_manager = settings_manager
        self.on_end_callback = on_end_callback
        # Consider removing --avcodec-hw=none if general playback is fine,
        # only add if specific videos cause decoding issues.
        #self.instance = vlc.Instance("--no-xlib --avcodec-hw=none") 
        #self.instance = vlc.Instance("--no-xlib --avcodec-hw=none --vout=wingdi")
        self.instance = vlc.Instance("--no-xlib") # Try default output firstself.instance = vlc.Instance("--no-xlib") # Try default output first
        self.player = None  # Will be created by _create_and_setup_player()
        self.embedded_frame_widget = None 
        self.current_media_path = None
        self.current_song_info = None
        self.embedded_frame_widget_id = None 
        
        # Event manager setup is now solely in _create_and_setup_player()
        # DO NOT ATTEMPT TO SETUP EVENTS HERE as self.player is None

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

    def play(self, video_path, song_info=None):
        # ... (this method should be as defined previously, including the logger.debug line that uses self.embedded_frame_widget_id) ...
        logger.info(f"== VideoPlayer.play - Play requested for: {video_path} ==")
        if not video_path:
            logger.error("No video path provided. Aborting play.")
            return

        logger.debug("VideoPlayer.play: Calling _create_and_setup_player()...")
        if not self._create_and_setup_player():
             logger.error("VideoPlayer.play: _create_and_setup_player() FAILED. Aborting play.")
             self._handle_media_error(None) 
             return
        logger.debug(f"VideoPlayer.play: _create_and_setup_player() SUCCEEDED. New player: {self.player}")
        
        # This debug line was causing the second error, it should now work
        logger.debug(f"VideoPlayer.play: Just before calling _embed_player. self.embedded_frame_widget_id = {self.embedded_frame_widget_id}, self.player = {self.player}")
        
        if not self._embed_player():
            logger.warning(f"VideoPlayer.play: _embed_player() indicated embedding might fail or use a new window for {video_path}.")

        try:
            logger.debug(f"VideoPlayer.play: Creating media for '{video_path}'")
            media = self.instance.media_new(video_path)
            if not media:
                logger.error(f"VideoPlayer.play: self.instance.media_new() FAILED for path: {video_path}. Aborting.")
                self._handle_media_error(None)
                return
            
            self.player.set_media(media)
            media.release() 
            logger.debug(f"VideoPlayer.play: Media set. Calling self.player.play().")

            play_result = self.player.play()
            logger.info(f"VideoPlayer.play: self.player.play() for '{video_path}' returned: {play_result}")

            if play_result == -1:
                logger.error(f"VideoPlayer.play: self.player.play() FAILED (returned -1) for {video_path}. Aborting.")
                self._handle_media_error(None)
                return
            
            self.current_media_path = video_path
            self.current_song_info = song_info
            logger.info(f"VideoPlayer.play: Playback INITIATED for: {song_info['artist'] if song_info else 'Unknown'} - {song_info['title'] if song_info else video_path}")

        except Exception as e:
            logger.error(f"VideoPlayer.play: EXCEPTION during play setup for {video_path}: {e}", exc_info=True)
            self.current_media_path = None
            self.current_song_info = None
            self._handle_media_error(None)
        logger.info(f"== VideoPlayer.play - FINISHED for: {video_path} ==")

    def _embed_player(self):
            """Internal method to perform embedding using the stored ID."""
            if self.player and self.embedded_frame_widget_id: # Condition inside _embed_player
                logger.debug(f"Attempting to embed NEW player {self.player} into frame ID: {self.embedded_frame_widget_id}")
                # ... embedding calls ...
            elif not self.player:
                logger.warning("_embed_player called but self.player is None.")
            elif not self.embedded_frame_widget_id: # <--- THIS IS THE MOST LIKELY CAUSE FOR THE SYMPTOM
                logger.warning("_embed_player called but no embedding frame ID is set.")

    def _handle_media_end(self, event):
        logger.info(f"VLC Event: MediaEnded for {self.current_media_path}")
        # No need to stop the player here, it has ended.
        # Clearing current_media_path tells our app the player is free.
        self.current_media_path = None 
        if self.on_end_callback:
            self.on_end_callback(event)
        logger.info(f"VLC Event: MediaEnded for {self.current_media_path}")

    def _handle_media_error(self, event):
        media_path_for_log = self.current_media_path or "unknown media (error triggered manually)"
        logger.error(f"VLC Event: MediaPlayerEncounteredError for {media_path_for_log}.")
        self.current_media_path = None 
        if self.on_end_callback:
            self.on_end_callback(event)

    def _embed_player(self):
        # ... (this method should be as defined previously, checking self.player and self.embedded_frame_widget_id) ...
        if not self.player:
            logger.warning("_embed_player: Called but self.player is None. Cannot embed.")
            return False 
        if not self.embedded_frame_widget_id:
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

    def embed_into_frame(self, frame_widget):
        """
        Embeds the VLC player into a Tkinter Frame.
        The frame_widget must be a Tkinter Frame or Toplevel window.
        """
        self.embedded_frame_widget = frame_widget # Store for later use
        if self.player and self.embedded_frame_widget:
            logger.debug(f"Embedding player into frame ID: {self.embedded_frame_widget.winfo_id()}")
            try:
                if platform.system() == "Linux":
                    self.player.set_xwindow(self.embedded_frame_widget.winfo_id())
                elif platform.system() == "Windows":
                    self.player.set_hwnd(self.embedded_frame_widget.winfo_id())
                elif platform.system() == "Darwin":
                    self.player.set_hwnd(self.embedded_frame_widget.winfo_id())
                logger.debug("Player embedding attempted.")
            except Exception as e:
                logger.error(f"Error embedding player: {e}")
        elif not self.player:
            logger.warning("Embed called but player not yet created.")
        elif not self.embedded_frame_widget:
            logger.warning("Embed called but frame widget is not set.")

    def set_embedding_widget(self, frame_widget):
        """Call this once from PlayerUI to set the target frame ID."""
        if frame_widget:
            try:
                widget_id = frame_widget.winfo_id()
                self.embedded_frame_widget_id = widget_id
                logger.info(f"Embedding frame ID SET to: {self.embedded_frame_widget_id}")
            except tk.TclError as e:
                logger.error(f"Error getting winfo_id for frame_widget in set_embedding_widget: {e}")
                self.embedded_frame_widget_id = None
        else:
            logger.error("set_embedding_widget called with None frame_widget.")
            self.embedded_frame_widget_id = None

    def play(self, video_path, song_info=None):
        logger.info(f"Play requested for: {video_path}") # THIS IS LOGGED for Alice Merton
        if not video_path:
            logger.error("No video path provided to player.")
            return

        # --- Code block A ---
        if not self._create_and_setup_player(): # Create/recreate player
             logger.error("Failed to create/setup player. Aborting play.")
             self._handle_media_error(None) # Ensure on_end_callback to try next
             return
        # --- End Code block A ---

        # --- Code block B ---
        logger.debug(f"VideoPlayer.play: Just before calling _embed_player. self.embedded_frame_widget_id = {self.embedded_frame_widget_id}, self.player = {self.player}")
        if self.embedded_frame_widget: # Re-embed if we have a frame
            self.embed_into_frame(self.embedded_frame_widget)
        else:
            logger.warning("No frame widget to embed into. Video might play in a separate window.")
        # --- End Code block B ---

        try:
            # --- Code block C ---
            media = self.instance.media_new(video_path)
            if not media:
                logger.error(f"Failed to create media object for path: {video_path}")
                self._handle_media_error(None) # Ensure on_end_callback to try next
                return
            self.player.set_media(media)
            media.release() # Media object can be released after set_media
            # --- End Code block C ---

            # --- Code block D ---
            play_result = self.player.play()
            if play_result == -1:
                logger.error(f"Failed to start playback for {video_path}. player.play() returned -1.")
                self._handle_media_error(None) # Ensure on_end_callback to try next
                return
            # --- End Code block D ---

            self.current_media_path = video_path
            self.current_song_info = song_info
            # THIS LOG IS MISSING for Alice Merton:
            logger.info(f"Playing: {song_info['artist'] if song_info else 'Unknown'} - {song_info['title'] if song_info else video_path}")

        except Exception as e:
            logger.error(f"Exception during play setup for {video_path}: {e}")
            self.current_media_path = None
            self.current_song_info = None
            self._handle_media_error(None) # Manually trigger error handling

    def stop(self):
        if self.player:
            logger.info(f"Stop called. Current media: {self.current_media_path}")
            self.player.stop()
        self.current_media_path = None
        self.current_song_info = None # Clear song info on explicit stop

    def pause(self):
        if self.player:
            self.player.pause()

    def set_volume(self, volume):
        if self.player:
            self.player.audio_set_volume(int(volume))

    def get_volume(self):
        return self.player.audio_get_volume() if self.player else 0

    def get_state(self):
        return self.player.get_state() if self.player else vlc.State.Ended # Default to Ended if no player

    def get_current_song_info(self):
        return self.current_song_info

    def release(self): # This is for app shutdown
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
        self.embedded_frame_widget_id = None # Clear the stored ID