from files.downloader import MassMusicDownloader
mmd = MassMusicDownloader()

mmd.clearTerminal()
print(
'''
 __  __           _        _____                      _                 _           
|  \/  |         (_)      |  __ \                    | |               | |          
| \  / |_   _ ___ _  ___  | |  | | _____      ___ __ | | ___   __ _  __| | ___ _ __ 
| |\/| | | | / __| |/ __| | |  | |/ _ \ \ /\ / / '_ \| |/ _ \ / _` |/ _` |/ _ \ '__|
| |  | | |_| \__ \ | (__  | |__| | (_) \ V  V /| | | | | (_) | (_| | (_| |  __/ |   
|_|  |_|\__,_|___/_|\___| |_____/ \___/ \_/\_/ |_| |_|_|\___/ \__,_|\__,_|\___|_|   
####################################################################################                                                                                                                                                                       
What playlist would you like to download from spotify?
Type "refresh" to refresh all the playlists downloaded
Type "done" to confirm all playlists downloaded
'''
)

mmd.run()