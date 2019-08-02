import os
import json
import threading
import time
import re

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock

from vk_api import VkApi
from vk_api.audio import VkAudio
import requests
from vk_api.exceptions import AuthError, AccessDenied, VkApiError, TwoFactorError
from requests.exceptions import ConnectionError as RequestError


CFG_NAME = 'vksvr_config.json'


def get_song_list(session, owner_id=None, album_id=None, access_hash=None):
    try:
        session.auth(reauth=True)
        au = VkAudio(session)
        return au.get(owner_id=owner_id, album_id=album_id, access_hash=access_hash)
    except RequestError:
        return 'Connection error'
    except TwoFactorError:
        return '2FA error'
    except AuthError:
        return 'Auth error'
    except AccessDenied:
        return 'Access denied'
    except VkApiError:
        return 'Request error'
    except TypeError:
        return 'Type error, :WTF:?!?!?!?'


def load_cfg(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except OSError:
        return {}
    except json.decoder.JSONDecodeError:
        return {}


def dumb_cfg(path, d):
    try:
        with open(path, 'w') as f:
            json.dump(d, f)
    except OSError:
        pass


def show_dialog(ret, title, button_text):
    MyPopup(ret, button_text, title=title).open()


class DownloadThread(threading.Thread):
    def __init__(self, app_path, widgets, *args, **kwargs):
        super(DownloadThread, self).__init__(*args, **kwargs)
        self._widgets = widgets
        self._kill_event = threading.Event()
        self._data = {
            'login': widgets['login'].text,
            'password': widgets['password'].text,
            'path': widgets['path'].text,
        }
        self._session = VkApi(login=self._data['login'],
                              password=self._data['password'],
                              config_filename=os.path.join(app_path, 'vk_config.v2.json'),
                              auth_handler=self.handle_2fa)
        self._cfg_path = os.path.join(app_path, CFG_NAME)
        self._popup_answer = None

    def run(self):
        self._widgets['status'].text = 'login...'
        songs = get_song_list(self._session)
        if songs is str:
            self._widgets['status'].text = songs
            return
        p = os.getcwd()
        os.chdir(self._data['path'])
        dumb_cfg(self._cfg_path, self._data)

        for i in os.listdir():
            if re.match(r'\d{4} .*', i):
                os.rename(i, i[5:])

        counter = 1
        size = len(songs)
        for i in songs:
            if self._kill_event.is_set():
                return
            r = requests.get(i['url'])
            if r.status_code == 200:
                song = f"{i['artist']} - {i['title']}.mp3"
                song = re.sub(r'[\\/:*?"<>|]', ' ', song)  # removing forbidden characters
                self._widgets['status'].text = song
                if not os.path.exists(song):
                    song = f"%04d {song}" % counter
                    with open(song, 'wb') as f:
                        f.write(r.content)
                elif os.path.isfile(song):
                    os.rename(song, f"%04d {song}" % counter)
            counter += 1
        self._widgets['status'].text = 'done!'
        os.chdir(p)

    def handle_2fa(self):
        ans = [None]
        Clock.schedule_once(lambda dt: show_dialog(ans, '2FA Code', 'Ok'))
        while ans[0] is None:
            time.sleep(.5)
            if self._kill_event.is_set():
                return
        return ans[0], False

    def kill(self):
        self._kill_event.set()


class MyApp(App):
    def __init__(self, **kwargs):
        super(MyApp, self).__init__(**kwargs)
        self._app_dir = os.path.normpath(os.path.realpath(self.directory))
        self._cfg_path = os.path.normpath(os.path.join(self._app_dir, 'vksvr_cfg.json'))
        self._widgets = {}
        self._download_thread = None

    def build(self):
        login = ''
        password = ''
        path = ''
        d = load_cfg(os.path.join(self._app_dir, CFG_NAME))
        if 'login' in d:
            login = d['login']
        if 'password' in d:
            password = d['password']
        if 'path' in d:
            path = d['path']

        self._widgets = {
            'login':    TextInput(text=login, multiline=0),
            'password': TextInput(text=password, multiline=0),
            'path':     TextInput(text=path, multiline=0),
            'status':   Label(text='status'),
            'button':   Button(text='Go!', on_release=self.handle_button)
        }
        main_widget = BoxLayout(orientation='vertical')
        for key, i in self._widgets.items():
            main_widget.add_widget(i)
        self._widgets['main'] = main_widget

        return self._widgets['main']

    def on_stop(self):
        if self._download_thread is not None:
            self._download_thread.kill()

    def handle_button(self, instance):
        self._download_thread = DownloadThread(self._app_dir, self._widgets)
        self._download_thread.start()


class MyPopup(Popup):
    def __init__(self, ret, button_text, **kwargs):
        kwargs['size_hint'] = (1, .5)
        super(MyPopup, self).__init__(**kwargs)
        self._ret = ret
        self._answer = None
        self._widgets = {
            'input': TextInput(multiline=0),
            'button': Button(text=button_text, on_release=self.handle_button)
        }
        main_widget = BoxLayout(orientation='vertical')
        for key, i in self._widgets.items():
            main_widget.add_widget(i)
        self._widgets['main'] = main_widget
        self.add_widget(main_widget)

    def handle_button(self, instance):
        self._answer = self._widgets['input'].text
        self.dismiss()

    def on_pre_dismiss(self):
        if self._answer is not None:
            self._ret[0] = self._answer
        else:
            self._ret[0] = ''


if __name__ == '__main__':
    MyApp().run()
