# core/video_player.py
import vlc
import platform
import logging
import tkinter as tk # For tk.TclError

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_end_callback=None):
        self.settings_manager = settings_manager
        self.on_end_callback = on_end_callback
        
        # Critical VLC Instance arguments for stability and embedding on Windows:
        # --no-xlib: Standard for non-X11.
        # --no-video-title-show: Prevents VLC from adding its own title to the window.
        # --avcodec-hw=none: Attempt to force software decoding.
        # --vout=direct3d11: Explicitly try to use Direct3D11 for output, which *should* embed.
        #   If this still causes D3D11VA errors on console and new windows,
        #   the next fallback is --vout=directdraw.
        #   If directdraw also creates new windows, then wingdi is last resort (but often new window).
        instance_args = [
            "--no-xlib",
            "--avcodec-hw=none", # Try to minimize hardware issues
            #"--no-video-title-show", # Helps keep window clean
            #"--quiet" # Reduces VLC's own console verbosity
        ]
        # We will let VLC choose its vout for now and focus on the player re-creation stability.
        # If new windows persist, we will experiment with --vout here.
        logger.info(f"VideoPlayer: Initializing VLC instance with args: {instance_args}")
        self.instance = vlc.Instance(instance_args)
        
        self.player = None 
        self.embedded_frame_widget_id = None
        self.current_media_path = None
        self.current_song_info = None

    def _create_and_setup_player(self): # Re-create player each time
        logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.1: ENTERED method.")
        old_player_ref = self.player 
        
        if old_player_ref:
            logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.2: Old player exists ({old_player_ref}). Will nullify ref & detach events.")
            try:
                logger.debug(f"Attempting to detach events from old player: {old_player_ref}")
                old_events = old_player_ref.event_manager()
                if old_events:
                    old_events.event_detach(vlc.EventType.MediaPlayerEndReached)
                    old_events.event_detach(vlc.EventType.MediaPlayerEncounteredError)
                    logger.debug(f"Detached events from old player {old_player_ref}.")
            except Exception as e_ev:
                logger.error(f"EXCEPTION detaching events from old player {old_player_ref}: {e_ev}", exc_info=True)
            # We are NOT calling .stop() or .release() on old_player_ref here to avoid hangs.
            # The old_player_ref will go out of scope.
        else:
            logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.2A: No old player to manage.")

        self.player = None # Ensure self.player is None before creating new
        logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.6A: self.player set to None.")
        
        logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.7: Attempting self.instance.media_player_new(). Instance: {self.instance}")
        try:
            new_player_candidate = self.instance.media_player_new()
            logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.8: media_player_new() returned: {new_player_candidate}")
        except Exception as e:
            logger.error(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.E2: EXCEPTION during media_player_new(): {e}", exc_info=True)
            new_player_candidate = None
            
        if not new_player_candidate:
            logger.error("VideoPlayer._create_and_setup_player - CHECKPOINT 4.9: FAILED to create new player. Returning False.")
            return False
        
        self.player = new_player_candidate 
        logger.info(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.10: New player ASSIGNED: {self.player}. Setting up events.")
        
        try:
            events = self.player.event_manager()
            if events:
                events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_media_end)
                events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._handle_media_error)
                logger.info("VideoPlayer._create_and_setup_player - CHECKPOINT 4.11: Events ATTACHED.")
            else:
                logger.error("VideoPlayer._create_and_setup_player - CHECKPOINT 4.12: FAILED to get event manager!")
                if self.player: self.player.release() # Clean up if event setup failed
                self.player = None
                return False
        except Exception as e:
            logger.error(f"VideoPlayer._create_and_setup_player - CHECKPOINT 4.E3: EXCEPTION during event setup: {e}", exc_info=True)
            if self.player: self.player.release() # Clean up
            self.player = None
            return False

        logger.info("== VideoPlayer._create_and_setup_player - CHECKPOINT 4.13: EXITING (SUCCESS) ==")
        return True

    # _handle_media_end, _handle_media_error as before
    def _handle_media_end(self, event):
        logger.info(f"VLC Event: MediaEnded for {self.current_media_path}")
        self.current_media_path = None 
        if self.on_end_callback: self.on_end_callback(event)

    def _handle_media_error(self, event):
        media_path_for_log = self.current_media_path or "unknown media (triggered manually)"
        logger.error(f"VLC Event: MediaPlayerEncounteredError for {media_path_for_log}.")
        self.current_media_path = None 
        if self.on_end_callback: self.on_end_callback(event)

    # set_embedding_widget as before
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
            
    # _embed_player as before (ensure logging is clear)
    def _embed_player(self):
        logger.info(f"== VideoPlayer._embed_player: ENTERED. Player: {self.player}. Stored Frame ID: {self.embedded_frame_widget_id} (Type: {type(self.embedded_frame_widget_id)}) ==")
        if not self.player: logger.warning("_embed_player: self.player is None."); return False 
        if not self.embedded_frame_widget_id: logger.warning(f"_embed_player: ID is None for player {self.player}. New window likely."); return False 
        try:
            logger.debug(f"_embed_player: Attempting embed: player {self.player} to ID {self.embedded_frame_widget_id}")
            if platform.system() == "Linux": self.player.set_xwindow(self.embedded_frame_widget_id)
            elif platform.system() == "Windows": self.player.set_hwnd(self.embedded_frame_widget_id)
            elif platform.system() == "Darwin": self.player.set_hwnd(self.embedded_frame_widget_id)
            logger.info(f"_embed_player: Embedding setup SUCCESSFUL for player {self.player} to ID {self.embedded_frame_widget_id}")
            return True 
        except Exception as e:
            logger.error(f"_embed_player: EXCEPTION embedding player {self.player} to ID {self.embedded_frame_widget_id}: {e}", exc_info=True)
            return False

    # play method with CHECKPOINTS as before
    def play(self, video_path, song_info=None):
        logger.info(f"== VideoPlayer.play - ATTEMPTING. Path: '{video_path}', Title: '{song_info.get('title', 'N/A') if song_info else 'N/A'}' ==")
        try:
            logger.info("VideoPlayer.play - CHECKPOINT 1: Inside try block, before path check.")
            if not video_path:
                logger.error(f"VideoPlayer.play - CHECKPOINT 2: video_path IS FALSY ('{video_path}'). Aborting.")
                if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
                return
            logger.info(f"VideoPlayer.play - CHECKPOINT 3: video_path ('{video_path}') is VALID. Proceeding...")
            logger.info("VideoPlayer.play - CHECKPOINT 4: Calling _create_and_setup_player()...")
            if not self._create_and_setup_player(): # This creates new self.player
                logger.error("VideoPlayer.play - CHECKPOINT 5: _create_and_setup_player() FAILED. Aborting.")
                if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
                return
            logger.info(f"VideoPlayer.play - CHECKPOINT 6: _create_and_setup_player() SUCCEEDED. Player: {self.player}")
            logger.info(f"VideoPlayer.play - CHECKPOINT 7: Before _embed_player. ID: {self.embedded_frame_widget_id}")
            
            if not self._embed_player(): # Call _embed_player for the NEW self.player
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
            self.current_media_path = None; self.current_song_info = None
            if hasattr(self, '_handle_media_error') and callable(self._handle_media_error): self._handle_media_error(None)
        logger.info(f"== VideoPlayer.play - ATTEMPT FINISHED for: {video_path} ==")

    # --- ALL OTHER METHODS (stop, pause, get_state, etc., release) ---
    # --- MUST BE PRESENT as per the previous complete version ---
    def stop(self):
        if self.player: logger.info(f"Stop called. Media: {self.current_media_path}. Player: {self.player}"); self.player.stop()
        self.current_media_path = None; self.current_song_info = None
    def pause(self):
        if self.player: self.player.pause()
    def set_volume(self, volume):
        if self.player: safe_volume = max(0, min(int(volume), 200)); self.player.audio_set_volume(safe_volume); logger.debug(f"Volume set to {safe_volume}")
    def get_volume(self):
        return self.player.audio_get_volume() if self.player else 0
    def get_state(self):
        return self.player.get_state() if self.player else vlc.State.Ended
    def get_current_song_info(self):
        return self.current_song_info

    def release(self): # For app shutdown
        logger.info("VideoPlayer.release called for app shutdown.")
        if self.player:
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
            self.player = None
            logger.debug("Final media player instance released.")
        if self.instance:
            logger.debug(f"Releasing VLC instance: {self.instance}")
            try: self.instance.release()
            except Exception as e: logger.error(f"EXCEPTION releasing VLC instance: {e}", exc_info=True)
            self.instance = None
            logger.info("VLC instance released successfully.")
        self.embedded_frame_widget_id = None