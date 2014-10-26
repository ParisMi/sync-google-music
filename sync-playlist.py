__author__ = ''
from gmusicapi import Mobileclient
import fnmatch
import os
from mutagen.mp3 import MP3


class Song:
    def __init__(self):
        self.title = ""
        self.artist = ""
        self.id = ""
        self.tags = []
    def index(self):
        return self.artist + self.title


#get all tags in "comments" section of metadata
def get_tags(id3_obj):
    return map(lambda str: str.replace("\n","").replace("\r",""), id3_obj["COMM::eng"].text[0].split(","))


def get_artist(id3_obj):
    return id3_obj["TPE1"].text[0]


#get the title of the mp3, or just the filename if the title doesn't exist
def get_title(id3_obj):
    return id3_obj["TIT2"].text[0]


#return a clean-looking representation of a list (for logging)
def clean_string(list):
    return ", ".join(list)

#get all playlists in the current directory
def get_all_playlists():
    print "getting all playlists in directory..."
    map_playlist = {}
    for root, dirnames, filenames in os.walk(os.getcwd()):
        for filename in fnmatch.filter(filenames, '*.m3u'):
            map_playlist[filename.replace(".m3u","")] = (os.path.join(root, filename))
    print "found playlists: " + clean_string(map_playlist.keys())
    return map_playlist

#load all songs in all playlist to a database and return it
def build_song_db(map_playlist):
    print "finding and tracking all songs mentioned in the playlists..."
    song_db = {}
    #for each playlist, read all lines and try to find referenced mp3
    for str_playlist_name in map_playlist.keys():
        playlist_path = map_playlist[str_playlist_name]
        #open each playlist .m3u in the list
        file_playlist = open(playlist_path)
        line = "x"
        #read each line. each line is a path to the song
        while line != "":
            line = file_playlist.readline().replace("\n","")
            if line == "": #if we are at an empty line, this signifies the end of the file. exit while loop
                break
            try:
                mp3 = MP3(line)
            except IOError:
                print "skipping",line,"was not accessible. does it exist?"
                continue
            try:
                str_artist = get_artist(mp3)
                str_title = get_title(mp3)
            except KeyError:
                print "skipping ",line,", it is missing artist/title data."
                continue
            try:
                song = song_db[str_title + str_artist]
            except KeyError: #if song does not exist in db
                #add song metadata
                song = Song()
                song.artist = str_artist
                song.title = str_title
                #add this song to the DB
                song_db[str_title + str_artist] = song
            #add this playlist to the song's playlists
            song.tags.append(str_playlist_name)
            print "loaded mp3 ", song.title,"to playlist",str_playlist_name
    return song_db

#tries to match all songs in the local database with ones on google music
def fill_in_song_ids(mobileclient, song_db):
    print "matching up local songs with their google music counterparts..."
    dict_list_songs = mobileclient.get_all_songs()
    for dict_song in dict_list_songs:
        try:
            song = song_db[dict_song["title"] + dict_song["artist"]]
        except KeyError:
            continue #did not find song in local library w/ that title/artist
        #fill in the ID with the matching one from google music
        song.id = dict_song["id"]
    print "failed to match the following songs:",clean_string(map(lambda song: song.title, filter(lambda song: song.id=="",song_db.values())))

#delete old playlists and upload new ones
def reload_playlists(mobileclient, song_db, map_playlist):
    dict_list_playlists = mobileclient.get_all_playlists()
    #delete existing playlists
    for playlist_name in map_playlist.keys():
        for dict_playlist in dict_list_playlists:
            if(playlist_name == dict_playlist["name"]):
                mobileclient.delete_playlist(dict_playlist["id"])
                print "deleted old playlist",dict_playlist["name"]
    #create new ones
    for playlist_name in map_playlist.keys():
        playlist_id = mobileclient.create_playlist(playlist_name)
        mobileclient.add_songs_to_playlist(playlist_id, map(lambda song: song.id, filter(lambda song: playlist_name in song.tags, song_db.values())))
        print "created new playlist: ",playlist_name

print "##########################"
print "## google playlist sync ##"
print "##########################"
print "looking for playlists in ", os.getcwd()
mobileclient = Mobileclient()
authed = False
while not authed:
    user = raw_input("email: ")
    passw = raw_input("pass: ")
    authed = mobileclient.login(user,passw)
#1. get all playlists
map_playlist = get_all_playlists()
#2. register all songs in playlists
song_db = build_song_db(map_playlist)
#3. map all songs in playlists to their google counterpart
fill_in_song_ids(mobileclient, song_db)
#4. update existing playlists (delete old, create new)
reload_playlists(mobileclient, song_db, map_playlist)

print "finished! reload google play and your playlists should be updated."