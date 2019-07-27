import os
import json

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label

from vk_api import VkApi
from vk_api.audio import VkAudio
import requests
from jconfig.jconfig import Config


class MyApp(App):
    def build(self):
        app_dir = os.path.realpath(self.directory)
        self.cfg = os.path.normpath(os.path.join(app_dir, 'vksvr_cfg.json'))
        self.vk_cfg = os.path.normpath(os.path.join(app_dir, 'vk_config.v2.json'))
        login = ''
        password = ''
        path = os.path.normpath(os.path.join(app_dir, 'music'))

        try:
            with open(self.cfg, 'r') as f:
                d = json.load(f)
                if 'login' in d:
                    login = d['login']
                if 'password' in d:
                    password = d['password']
                if 'path' in d:
                    path = d['path']
        except OSError:
            pass

        self.widgets = {
            'login':    TextInput(text=login),
            'password': TextInput(text=password),
            'path':     TextInput(text=path),
            'status':   Label(text='status'),
            'button':   Button(text='Go!', on_press=lambda instance: self.download())
        }
        main_widget = BoxLayout(orientation='vertical')
        for kev, i in self.widgets.items():
            main_widget.add_widget(i)
        self.widgets['main'] = main_widget

        return self.widgets['main']

    def download(self):
        login = self.widgets['login'].text
        password = self.widgets['password'].text
        path = self.widgets['path'].text
        p = os.getcwd()
        os.chdir(path)

        session = VkApi(login=login, password=password, config_filename=self.vk_cfg)
        session.auth(reauth=True)
        au = VkAudio(session)
        songs = au.get()

        counter = 1
        for i in songs:
            r = requests.get(i['url'])
            if r.status_code == 200:
                song = f"%04d {i['artist']} - {i['title']}.mp3" % counter
                if os.path.exists(song):
                    pass
                else:
                    with open(song, 'wb') as f:
                        f.write(r.content)
            else:  # r.status_code == 200
                pass
            counter += 1

        os.chdir(p)

        try:
            with open(self.cfg, 'w') as f:
                d = {
                    'login': login,
                    'password': password,
                    'path': path
                }
                json.dump(d, f)
        except OSError:
            pass

        self.widgets['status'].text = 'done!'


MyApp().run()
