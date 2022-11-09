import validators, spotipy, re, os, json, yt_dlp, promptlib, eyed3, requests, time, sys
from youtube_search import YoutubeSearch
from PIL import Image
import numpy as np

class MassMusicDownloader:
    def __init__(self) -> None:
        self.spotifyPlaylistDefaultURL = 'https://open.spotify.com/playlist/'
        self.sp = self.envCheck()
        self.path = None
        self.refresh = False

        self.playlistURIs = []
        self.playlistLinks = []

        self.nErrors = []

        self.nAlreadyExist = 0
        self.nTotalSongs = 0

        self.buffer = 10

    def envCheck(self):
        client_ID = 'fa49dc6aa2404dc785b015d078bf8402'
        client_Secret = '4ddfc40fc9764312a8c51a4eaaea9bea'

        client_credentials_manager = spotipy.SpotifyClientCredentials(client_ID, client_Secret)
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

        return sp

    def getPath(self):
        if self.path == None:
            prompter = promptlib.Files()
            self.path = prompter.dir() + '/Spotify Playlists'
        
        if not os.path.exists(self.path):
            os.mkdir(self.path)
            os.mkdir(self.path + '/playlists')
            open(self.path + '/playlists/allPlaylists.txt', "a").close()
        
    def getURI(self, link):    
        return link.split("/")[-1].split("?")[0]
        
    def removeDuplicates(self, listOfURIs):
        return list(dict.fromkeys(listOfURIs))

    def askForPlaylists(self):
        self.playlistInput = None
        self.refresh = False

        while True:
            self.playlistInput = input('Link: ')

            if self.playlistInput == 'done':
                break
                
            elif self.playlistInput == 'refresh':
                self.refresh = True
                break

            elif validators.url(self.playlistInput) and self.spotifyPlaylistDefaultURL in self.playlistInput:
                self.playlistURIs.append(self.getURI(self.playlistInput))
                self.playlistLinks.append(self.playlistInput)

                self.addPlaylistsToDefault(self.playlistInput)

            else:
                print("Please enter a valid spotify playlist")

        self.playlistURIs = self.removeDuplicates(self.playlistURIs)

    def cleanText(self, str):
        str = re.sub('[><"|\?*]', "", str)
        str = re.sub("[/:]", "_", str)
        if "." in str:
            lastchar_index = str.rfind(".")
            str = str[:lastchar_index] + "#" + str[lastchar_index + 1 :]
        return str

    def getSongDetails(self, URI, needInfo=True):
        trackRawData = self.sp.playlist_tracks(URI)
        trackItems = trackRawData['items']

        while trackRawData["next"]:
            trackRawData = self.sp.next(trackRawData)
            trackItems.extend(trackRawData["items"])

        cleanSongInfo = []
        nSongs = 0
        for info in trackItems:
            if needInfo:
                info = info['track']

                try:
                    cleanSongInfo.append(
                        {
                            'trackName': self.cleanText(info["name"]),
                            'trackNameNoFormat': info["name"],

                            'trackArtist': info["artists"][0]["name"],

                            'trackAlbumName': self.cleanText(info["album"]["name"]),
                            'trackAlbumNameNoFormat': info["album"]["name"],

                            'trackAlbumCoverURL': info["album"]["images"][0]["url"],
                            'trackNum': info['track_number'],
                            'trackDuration': info['duration_ms']
                        }
                    )
                except:
                    print("Error getting song details")
            nSongs += 1
        
        return cleanSongInfo, nSongs

    def clearTerminal(self):
        os.system('cls')

    def find_nearest(self, lst, K):
        lst = np.asarray(lst)
        idx = (np.abs(lst - K)).argmin()
        return lst[idx]

    def passTimeToSeconds(self, input):
        total = 0
        splitedTotal = input.split(':')

        if len(splitedTotal) != 3:
            for i in range(3-len(splitedTotal)):
                splitedTotal.insert(0, 0)
        
        total += int(splitedTotal[0])*3600 + int(splitedTotal[1])*60 + int(splitedTotal[2])
        return total

    def getYTLink(self, song):
        results = YoutubeSearch(f"{song['trackName']} {song['trackArtist']} lyrics", max_results=10).to_json()
        data = json.loads(results)

        baseUrl = "https://www.youtube.com/watch?v="
        url = None

        durations = []
        urls = []

        trackDuration = song['trackDuration']/1000
        for v in data['videos']:
            videoID = v["id"]
            duration = self.passTimeToSeconds(v['duration'])
            videoURL = baseUrl + videoID
            url = videoURL

            durations.append(duration)
            urls.append(url)
        
        nearest = self.find_nearest(durations, trackDuration)
    
        return urls[durations.index(nearest)]

    def getSongPath(self, song):
        return f"{self.path}/{song['trackAlbumName']}/{song['trackName']}.mp3"

    def id3Tags(self, song):
        try:
            audiofile = eyed3.load(self.getSongPath(song))

            audiofile.tag.artist = song['trackArtist']
            audiofile.tag.album = song['trackAlbumNameNoFormat']
            audiofile.tag.title = song['trackNameNoFormat']
            audiofile.tag.track_num = song['trackNum']

            audiofile.tag.save()
        
        except:
            print(f"There was an error modifying {song['trackNameNoFormat']}'s metadata...")

    def getAlbumCover(self, song):
        coverURL = song['trackAlbumCoverURL']
        img = Image.open(requests.get(coverURL, stream = True).raw)

        img.save(self.path + '/' + song['trackAlbumName'] + '/cover.jpg')

    def getPlaylistName(self, uri):
        return self.sp.playlist(uri)["name"]

    def checkIfAlreadyExists(self, song):
        return os.path.exists(self.getSongPath(song))

    def playlistFolder(self, playlistName, relativeDirectories):
        playlistsPath = self.path + "/playlists"
        with open((playlistsPath + '/' + self.cleanText(playlistName) + '.m3u8'), "w", encoding="utf-8") as f:
            f.truncate(0)
            for dirs in relativeDirectories:
                f.write("%s\n" % (dirs))

    def addPlaylistsToDefault(self, linkInput):
        playlistsPath = self.path + "/playlists"

        with open((playlistsPath + '/' + 'allPlaylists.txt'), 'a+') as f:
            f.seek(0)
            exists = False
            for link in self.getDownloadedPlaylists():       
                if re.search(self.getURI(linkInput), link):
                    exists = True
                    break

            if not exists:
                f.write(linkInput + '\n')
                print("Playlist added to the list!")

    def convertSeconds(self, sec):
        sec = sec % (24 * 3600)
        hour = sec // 3600
        sec %= 3600
        min = sec // 60
        sec %= 60
        return "%02d:%02d:%02d" % (hour, min, sec) 

    def getDownloadedPlaylists(self):
        output = []
        with open(self.path + '/playlists/allPlaylists.txt', 'r') as reader:
            for line in reader.readlines():
                output.append(line[:len(line) - 2])
        
        return output

    def getArgs(self):
        args = sys.argv[1:]

        self.path = args[0] + '/Spotify Playlists'   

        self.refresh = False
        if args[1] == 'refresh':
            self.refresh = True
            for playlist in args[2:]:
                self.playlistURIs.append(self.getURI(playlist))
                self.playlistLinks.append(playlist)

                self.addPlaylistsToDefault(playlist)
        
        else:
            for playlist in args[1:]:
                self.playlistURIs.append(self.getURI(playlist))
                self.playlistLinks.append(playlist)

                self.addPlaylistsToDefault(playlist)


    #####################################################################################################
    #####################################################################################################
    #####################################################################################################

    def downloadSong(self, song):
        ytLink = self.getYTLink(song)
        
        # YouTube downloader options
        ydl_opts = {
            "quiet": True,
            "format": "bestaudio/best",
            "outtmpl": f"{self.path}/{song['trackAlbumName']}/{song['trackName']}.%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
                {"key": "FFmpegMetadata"},
            ],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(ytLink, download=True)
        
        self.id3Tags(song)
        self.getAlbumCover(song)

    def downloadPlaylist(self, playlistURI, playlistIndexInfo):
        allSongs = self.getSongDetails(playlistURI)[0]
        playlistName = self.getPlaylistName(playlistURI)

        self.nTotalSongs += len(allSongs)
        self.listOfRelativeDirectories = []
        for song in allSongs:
            self.listOfRelativeDirectories.append(f"../{song['trackAlbumName']}/{song['trackName']}.mp3")
            if not self.checkIfAlreadyExists(song):
                self.clearTerminal()

                stats = f'#  Playlist ({playlistName}): [{playlistIndexInfo[0]}/{playlistIndexInfo[1]}]  #  Song: [{allSongs.index(song)+1}/{len(allSongs)}]  #'

                if song['trackNameNoFormat'] == song['trackAlbumNameNoFormat']:
                    songDownloadStat = f"Downloading {song['trackNameNoFormat']} by {song['trackArtist']}!"
                else:
                    songDownloadStat = f"Downloading {song['trackNameNoFormat']} by {song['trackArtist']} from {song['trackAlbumNameNoFormat']}!"

                print('#'*len(stats))
                print(stats)

                if len(stats) > len(songDownloadStat):
                    print('#'*len(stats))
                else:
                    print('#'*len(songDownloadStat))

                print(songDownloadStat)
                print('#'*len(songDownloadStat))

                try:
                    self.downloadSong(song)
                except:
                    self.nErrors.append(song['trackNameNoFormat'])
                    self.nTotalSongs -= 1

            else:
                print(f"[{allSongs.index(song)+1}/{len(allSongs)}]: {song['trackNameNoFormat']} already exists!")
                self.nAlreadyExist += 1
        
        self.playlistFolder(playlistName, self.listOfRelativeDirectories)

        print("/"*50)

    def mainDownload(self):
        if self.refresh:
            for link in self.getDownloadedPlaylists():
                self.playlistURIs.append(self.getURI(link))

        startTime = time.time()
        for playlistURI in self.playlistURIs:
            self.downloadPlaylist(playlistURI, [self.playlistURIs.index(playlistURI)+1, len(self.playlistURIs)])
        

        self.clearTerminal()
        print("/"*50)

        print(f"It took {self.convertSeconds(time.time()-startTime)} to download {self.nTotalSongs} songs...")
        print(f"{self.nAlreadyExist} songs already existed and were not downloaded again!")

        songErrorLen = len(self.nErrors)
        if songErrorLen != 0:
            print(f"[{songErrorLen}]: Songs failed: {self.nErrors}")


    def run(self):
        if len(sys.argv) != 1:
            self.getArgs()

        else:
            self.getPath()
            self.askForPlaylists()

        self.mainDownload()
        os.remove('.cache')