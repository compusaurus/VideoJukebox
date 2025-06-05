import os
import vlc
import platform
import logging

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_media_list_player_event=None):
        self.settings_manager = settings_manager
        self.on_media_list_player_event = on_media_list_player_event
        logger.info("Initializing VideoPlayer with MediaListPlayer approach.")
        vlc_args = [
            "--no-qt-privacy-ask",
            "--no-metadata-network-access",
            "--no-stats",
            "--no-video-title-show",
        ]
        log_file_path = "vlc_native_from_class.txt" 
        vlc_args.extend([
            "--verbose=2",
            f"--logfile={log_file_path}",
            "--logmode=text",
            "--file-logging"
        ])
        try:
            logger.info(f"Attempting vlc.Instance with args: {vlc_args}")
            self.instance = vlc.Instance(vlc_args)
            logger.info(f"VLC Instance CREATED: {self.instance}")
            import time
            time.sleep(0.2)
            logger.info("Short delay after VLC Instance creation.")
        except Exception as e:
            logger.error(f"Failed to create VLC instance with args {vlc_args}: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize VLC Instance for VideoPlayer. Args: {vlc_args}") from e

        # Create the VLC MediaList and MediaListPlayer
        self.media_list = self.instance.media_list_new()
        if self.media_list is None:
            logger.error("self.instance.media_list_new() FAILED (returned None).")
            if self.instance:
                self.instance.release()
            raise RuntimeError("Could not create VLC MediaList.")
        else:
            logger.info(f"VLC MediaList CREATED: {self.media_list}")

        self.ml_player = self.instance.media_list_player_new()
        if not self.ml_player:
            logger.error("Failed to create VLC MediaListPlayer.")
            if self.instance:
                self.instance.release()
            if self.media_list:
                self.media_list.release()
            raise RuntimeError("Could not create VLC MediaListPlayer.")
        logger.info(f"VLC MediaListPlayer CREATED: {self.ml_player}")

        # Tell the MediaListPlayer to use that list
        self.ml_player.set_media_list(self.media_list)

        # Grab the underlying MediaPlayer so we can embed, attach events, etc.
        self.media_player = self.ml_player.get_media_player()
        if not self.media_player:
            logger.error("Failed to get MediaPlayer from MediaListPlayer.")
            if self.instance:
                self.instance.release()
            if self.media_list:
                self.media_list.release()
            if self.ml_player:
                self.ml_player.release()
            raise RuntimeError("Could not get MediaPlayer from MediaListPlayer.")
        logger.info(f"Underlying MediaPlayer obtained: {self.media_player}")

        self.embedded_frame_widget_id = None
        self.current_song_info = None

        # Attach VLC events
        mlp_events = self.ml_player.event_manager()
        if mlp_events:
            mlp_events.event_attach(vlc.EventType.MediaListPlayerNextItemSet, self._handle_next_item_set)
        else:
            logger.warning("Could not get event manager for MediaListPlayer.")

        player_events = self.media_player.event_manager()
        if player_events:
            player_events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_single_media_ended)
            player_events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._handle_media_error)
        else:
            logger.warning("Could not get event manager for underlying MediaPlayer.")
        logger.info("VideoPlayer initialization complete.")

    def _handle_next_item_set(self, event):
        """
        Called when VLC is about to start the next item in the list.
        We re-embed the new MediaPlayer (so video still shows inside our Tk frame),
        then fire our own “NextItemSet” event so the UI knows what’s about to play.
        """
        
        logger.info(f"MediaListPlayer Event: NextItemSet received (event type: {event.type})")
        # 1) Figure out the new MRL that VLC is about to play:
        next_mrl = None
        if self.media_player:
            m = self.media_player.get_media()
            if m:
                next_mrl = m.get_mrl()
                logger.info(f"MediaListPlayer Event: NextItemSet. Current media on player MRL: {next_mrl}")
                m.release()
            else:
                logger.warning("MediaListPlayer Event: NextItemSet, but get_media() returned None.")
        else:
            logger.warning("MediaListPlayer Event: NextItemSet, but self.media_player is None.")

        # 2) Re-embed the new media_player into our Tk frame (so the video actually shows)
        if self.embedded_frame_widget_id:
            try:
                self._embed_player()
            except Exception as e:
                logger.error(f"Error with re-embedding on NextItemSet: {e}", exc_info=True)

        # 3) Notify the main app about “NextItemSet”:
        if self.on_media_list_player_event:
            self.on_media_list_player_event(event_type="NextItemSet", mrl=next_mrl)

    def _handle_single_media_ended(self, event):
        """
        Called when the current item finishes.
        We remove index 0 from ``self.media_list`` (the video that just ended),
        then fire the ``SingleMediaEnded`` event so the UI can update its queue,
        and finally call ``ml_player.play()`` again if there is another item
        remaining.  This helps ensure continuous playback when multiple videos
        have been queued.
        """
        # 1) Log what just ended
        current_song_title = self.current_song_info.get('title', 'N/A') if self.current_song_info else 'Unknown'
        logger.info(f"MediaPlayer Event: MediaPlayerEndReached for item: {current_song_title}")
 
        # 2) Grab the actual MRL of the finished media
        actual_mrl = None
        if self.media_player:
            m = self.media_player.get_media()
            if m:
                actual_mrl = m.get_mrl()
                m.release()

        # 3) Remove index 0 from VLC’s media_list (the just-played item)
        if self.media_list and self.media_list.count() > 0:
            self.media_list.lock()
            try:
                logger.debug(
                    f"Removing finished item at index 0 from VLC MediaList "
                    f"(MRL: {actual_mrl}). Count before removal: {self.media_list.count()}"
                )
                result = self.media_list.remove_index(0)
                if result == 0:
                    logger.info(
                        f"Successfully removed finished item (was MRL: {actual_mrl}) "
                        f"from VLC MediaList. New count: {self.media_list.count()}"
                    )
                else:
                    logger.error(
                        f"Failed to remove item at index 0 "
                        f"(was MRL: {actual_mrl}) from VLC MediaList (error code: {result})."
                    )
            except Exception as e:
                logger.error(f"Exception removing item from VLC MediaList: {e}", exc_info=True)
            finally:
                self.media_list.unlock()

        # 4) Notify the app that “SingleMediaEnded” occurred
        if self.on_media_list_player_event:
            self.on_media_list_player_event(event_type="SingleMediaEnded", mrl=actual_mrl)

        # 5) If there’s still at least one item in the list, start playback again
        if self.media_list and self.media_list.count() > 0:
            logger.info(
                "_handle_single_media_ended: Next item exists; calling ml_player.play() to continue."
            )
            next_result = self.ml_player.play()
            # python-vlc may return None on success; treat anything other than -1 as success
            if next_result not in (-1,):
                logger.info(
                    "_handle_single_media_ended: ml_player.play() invoked for next item."
                )
            else:
                logger.error(
                    f"_handle_single_media_ended: ml_player.play() FAILED with code {next_result}."
                )
                if self.on_media_list_player_event:
                    self.on_media_list_player_event(event_type="MediaError")

    def _handle_media_error(self, event):
        logger.error("MediaPlayer Event: MediaPlayerEncounteredError.")

    def set_embedding_widget(self, frame_widget):
        """Call this once from PlayerUI to set the target frame."""
        if frame_widget:
            self.embedded_frame_widget_id = frame_widget.winfo_id()
            logger.info(f"Embedding frame ID set: {self.embedded_frame_widget_id}")
            if self.media_player and self.embedded_frame_widget_id:
                self._embed_player()
        else:
            logger.error("set_embedding_widget called with None frame_widget.")

    def _embed_player(self):
        """Internal method to perform embedding using the stored ID."""
        if self.media_player and self.embedded_frame_widget_id:
            logger.debug(f"Attempting to embed MediaPlayer {self.media_player} into frame ID: {self.embedded_frame_widget_id}")
            try:
                if platform.system() == "Linux":
                    self.media_player.set_xwindow(self.embedded_frame_widget_id)
                elif platform.system() == "Windows":
                    self.media_player.set_hwnd(self.embedded_frame_widget_id)
                elif platform.system() == "Darwin":
                    self.media_player.set_nsobject(self.embedded_frame_widget_id)
                logger.info(f"MediaPlayer embedding setup for frame ID: {self.embedded_frame_widget_id}")
            except Exception as e:
                logger.error(f"Error during MediaPlayer embedding: {e}", exc_info=True)

    def add_to_playlist(self, video_path, song_info):
        logger.info(f"ADD_TO_PLAYLIST CALLED FOR: {video_path}")

        if self.instance is None or self.ml_player is None or self.media_list is None:
            logger.error("ADD_TO_PLAYLIST: one of the VLC objects is None. Cannot proceed.")
            return False

        if not bool(self.instance) or not bool(self.ml_player):
            logger.error("ADD_TO_PLAYLIST: VLC wrapper objects exist but evaluate to False. Cannot proceed.")
            return False

        if not bool(self.media_list):
            logger.warning("ADD_TO_PLAYLIST: self.media_list (empty) is False, but VLC can still add media to an empty list.")

        try:
            media = self.instance.media_new(video_path)
            if not media:
                logger.error(f"ADD_TO_PLAYLIST: self.instance.media_new('{video_path}') returned None.")
                return False

            media.set_meta(vlc.Meta.NowPlaying, f"{song_info.get('artist','')} - {song_info.get('title','')}")
            logger.debug(f"ADD_TO_PLAYLIST: Attempting self.media_list.add_media() for {media.get_mrl()}")
            result_add = self.media_list.add_media(media)
            media.release()

            if result_add == 0:
                logger.info(f"Successfully added '{video_path}' to self.media_list. VLC MediaList count: {self.media_list.count()}")
                return True
            else:
                logger.error(f"ADD_TO_PLAYLIST: self.media_list.add_media() for '{video_path}' returned code {result_add}.")
                return False
        except Exception as e:
            logger.error(f"ADD_TO_PLAYLIST: EXCEPTION while creating or adding media: {e}", exc_info=True)
            return False

    def play_playlist(self):
        """
        When the UI asks us to start the playlist, we simply call ml_player.play()
       (instead of play_item_at_index(0)) on the very first track.
        """
        if not (self.ml_player and self.media_list):
            logger.error("play_playlist: MediaListPlayer or MediaList not initialized. Cannot play.")
            return False

        total_items = self.media_list.count()
        if total_items == 0:
            logger.info("play_playlist: Playlist is empty. Nothing to play.")
            if self.on_media_list_player_event:
                self.on_media_list_player_event(event_type="PlaylistEmptyOrEnded")
            return False

        state = self.ml_player.get_state()
        logger.info(f"play_playlist called. Current MLP state: {state}. MediaList count: {total_items}")
 
        # 1) If empty, we already returned above. Now, if not already playing/buffering/opening,
        #    we call play(), which will start index 0 for the very first item.
        if state not in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering]:
            logger.info("MediaListPlayer is not active. Calling ml_player.play() to start playback.")
            result = self.ml_player.play()    # <— STILL use play() here for the first track
            # The bindings may return None when successful; only -1 indicates failure
            if result in (-1,):
                logger.error(f"play_playlist: ml_player.play() FAILED with code {result}.")
                if self.on_media_list_player_event:
                    self.on_media_list_player_event(event_type="MediaError")
            else:
                logger.info("play_playlist: ml_player.play() invoked.")
            return True

    def stop(self):
        if self.ml_player:
            logger.info("Stopping MediaListPlayer.")
            self.ml_player.stop()
        self.current_song_info = None

    def pause(self):
        if self.ml_player:
            self.ml_player.pause()

    def set_volume(self, volume):
        if self.media_player:
            self.media_player.audio_set_volume(int(volume))

    def get_volume(self):
        return self.media_player.audio_get_volume() if self.media_player else 0

    def get_playlist_count(self):
        return self.media_list.count() if self.media_list else 0

    def get_state(self):
        return self.ml_player.get_state() if self.ml_player else vlc.State.Ended

    def get_current_song_info_from_player(self):
        if self.media_player:
            current_media = self.media_player.get_media()
            if current_media:
                mrl = current_media.get_mrl()
                current_media.release()
                return {"mrl": mrl}
        return None

    def release(self):
        logger.warning("== VIDEO_PLAYER.RELEASE() CALLED ==")
        logger.info("VideoPlayer (MediaList approach) release called.")

        if self.ml_player:
            logger.debug(f"Stopping and releasing MediaListPlayer: {self.ml_player}")
            self.ml_player.stop()
            try:
                mlp_events = self.ml_player.event_manager()
                if mlp_events:
                    mlp_events.event_detach(vlc.EventType.MediaListPlayerNextItemSet)
            except Exception as e:
                logger.warning(f"Exception detaching events from ml_player: {e}")
            self.ml_player.release()
            self.ml_player = None
            logger.debug("MediaListPlayer released.")

        if self.media_player:
            logger.debug(f"Releasing underlying MediaPlayer: {self.media_player}")
            try:
                player_events = self.media_player.event_manager()
                if player_events:
                    player_events.event_detach(vlc.EventType.MediaPlayerEndReached)
                    player_events.event_detach(vlc.EventType.MediaPlayerEncounteredError)
            except Exception as e:
                logger.warning(f"Exception detaching events from media_player: {e}")
            self.media_player = None
            logger.debug("Underlying MediaPlayer reference nullified.")

        if self.media_list:
            logger.debug(f"Releasing MediaList: {self.media_list}")
            self.media_list.release()
            self.media_list = None
            logger.debug("MediaList released.")

        if self.instance:
            logger.debug(f"Releasing VLC Instance: {self.instance}")
            self.instance.release()
            self.instance = None
            logger.debug("VLC Instance released.")
        logger.info("VideoPlayer resources effectively released.")
