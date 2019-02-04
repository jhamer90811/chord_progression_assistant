#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2/2/18

Author: Jesse Hamer

The Data Incubator Application

Challenge 3: Propose a Project

Working Project Title: Sentiment Analysis of Chord Progressions
"""

import requests
import time
import json
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

HOOKTHEORY_USERNAME = 'your_username_here'
HOOKTHEORY_PWORD = 'your_password_here'
HOOKTHEORY_API_ENDPT = 'https://api.hooktheory.com/v1/'

HT_AUTH_REQUEST_URL = HOOKTHEORY_API_ENDPT + 'users/auth'

HT_AUTH_REQUEST_BODY = {'username': HOOKTHEORY_USERNAME,
                     'password': HOOKTHEORY_PWORD}

HT_AUTH_REQUEST_RESP = requests.request('POST',
                                        HT_AUTH_REQUEST_URL,
                                        json=HT_AUTH_REQUEST_BODY)

HT_AUTH_REQUEST_CONTENT = HT_AUTH_REQUEST_RESP.json()

ht_activation_key = 'Bearer ' + HT_AUTH_REQUEST_CONTENT['activkey']

ht_auth_header = {'Authorization': ht_activation_key}

client = requests.session()
client.headers = ht_auth_header

def get_song_request(sess, cp, wait_time=0, verbose=False):
    songs = []
    
    page = 0
    redo=True
    new_songs=[]
    
    while new_songs or redo:
        songs+=new_songs
        page+=1
        redo=False
        
        r = sess.get(HOOKTHEORY_API_ENDPT + 'trends/songs', 
                     params = {'cp':cp, 'page':str(page)})
        new_songs = r.json()
        
        remaining = int(r.headers['X-Rate-Limit-Remaining'])
        wait_time = int(r.headers['X-Rate-Limit-Reset'])
        
        if verbose:
            print('Retrieved page {}; contains {} new results'.format(page,
                  len(new_songs)))
            
        if remaining==0:
            print('Too many requests. Waiting {} seconds...'.format(wait_time))
            time.sleep(wait_time)
        if False in [type(s)==dict for s in new_songs]:
            page-=1
            new_songs=[]
            redo=True
            
    return songs


def get_chord_progressions(sess, initial_progressions, tol = 0, verbose=False):
    chord_progs = []
    initial_progs = initial_progressions.copy()
    
    while initial_progs:
        prog = initial_progs.pop(0)
        cp= prog['child_path']
        
        r = sess.get(HOOKTHEORY_API_ENDPT + 'trends/nodes', 
                     params = {'cp':cp})
        new_prog = r.json()
        
        remaining = int(r.headers['X-Rate-Limit-Remaining'])
        wait_time = int(r.headers['X-Rate-Limit-Reset'])
            
        if remaining==0:
            print('Too many requests. Waiting {} seconds...'.format(wait_time))
            time.sleep(wait_time)
        if False in [type(s)==dict for s in new_prog]:
            initial_progs.insert(0, prog)
        else:
            new_prog = [p for p in new_prog if p['probability']>tol]
            chord_progs+=new_prog
            if verbose:
                print('Progression {} processed.'.format(cp))
            
            
    return chord_progs

one_chord = get_chord_progressions(client, [{'child_path':''}], tol=0.05, verbose=True)

two_chord = get_chord_progressions(client, one_chord, tol=0.05, verbose=True)

three_chord = get_chord_progressions(client, two_chord, tol=0.05, verbose=True)

four_chord = get_chord_progressions(client, three_chord, tol=0.05, verbose=True)

five_chord = get_chord_progressions(client, four_chord, tol=0.05, verbose=True)

def get_cp_song_data(sess, chord_progs, verbose=0):
    data = pd.DataFrame([], columns=['cp', 'artist', 'song', 'section'])
    total_cp = len(chord_progs)
    cp_counter = 0
    
    if verbose==0:
        songs_verbose=False
        cp_verbose=False
    if verbose==1:
        songs_verbose=False
        cp_verbose=True
    if verbose==2:
        songs_verbose=True
        cp_verbose=True
    
    for prog in chord_progs:
        cp_counter+=1
        cp = prog['child_path']
        if cp_verbose:
            print('###### FETCHING SONGS FOR {}; {}/{} ##########\n'.format(cp,
                  cp_counter, total_cp))
        songs = get_song_request(sess, cp, verbose=songs_verbose)
        for song in songs:
            song['cp'] = cp
            song.pop('url')
        data = data.append(songs)
        if cp_verbose:
            print('###### DONE WITH {}; {} SONGS ADDED; DATA SHAPE: {} #########\n'.format(cp,
                  len(songs), data.shape))
    return data

# Get data for four-chord progressions first, to make sure everything works.
        
cp_song_data_four = get_cp_song_data(client, four_chord, verbose=1)

cp_song_data_four.song = cp_song_data_four.song.apply(lambda x: x.lower())
cp_song_data_four.artist = cp_song_data_four.artist.apply(lambda x: x.lower())
cp_song_data_four.section= cp_song_data_four.section.apply(lambda x: x.lower())

print(cp_song_data_four.describe())

# 2220 unique artists, 3746 unique songs; 22 unique sections

print(cp_song_data_four.groupby(['artist', 'song']).size().shape[0])

# 3874 unique artist/song combinations

cp4_artist_song = cp_song_data_four[['artist', 'song']]
cp4_artist_song.drop_duplicates(inplace=True)
cp4_artist_song.sort_values(by=['artist', 'song'], inplace=True)
cp4_artist_song.reset_index(inplace=True, drop=True)



##############################################

# Now try to retrieve spotify information for each artist/song    

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

SPOTIFY_CLIENT_ID = 'your_spotify_client_id_here'

SPOTIFY_CLIENT_SECRET = 'your_spotify_client_secret_here'

token = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                 client_secret=SPOTIFY_CLIENT_SECRET)

cache_token = token.get_access_token()

spotify = Spotify(cache_token)

def get_track_ids(client, data, num_tracks=None, turn_update=None):
    
    for i, row in data.iterrows():
        artist=row['artist']
        song=row['song']
        q = 'artist:'+artist + ' ' + 'track:'+song
        result = client.search(q)
        items = result['tracks']['items']
        if not items:
            continue
        popularities = [item['popularity'] for item in items]
        most_popular = items[popularities.index(max(popularities))]
        data.loc[(data.artist==artist) & (data.song==song),'spotify_ID']=most_popular['id']
        if i == num_tracks:
            break
        if turn_update and (i+1)%turn_update==0:
            print('Finished track {}'.format(i+1))
            
get_track_ids(spotify, cp4_artist_song)
    
def get_audio_features(client, data, verbose=False):
    
    ids = data.spotify_ID.dropna()
    
    audio_feature_data = pd.DataFrame([],columns=['danceability', 'energy',
                                      'key', 'loudness', 'mode', 'speechiness',
                                      'acousticness', 'instrumentalness',
                                      'liveness', 'valence', 'tempo','id',
                                      'duration_ms', 'time_signature'])
    for i in range(0, len(ids), 50):
        new_features = spotify.audio_features(ids[i:i+50])
        for track in new_features:
            track.pop('type')
            track.pop('uri')
            track.pop('track_href')
            track.pop('analysis_url')
        audio_feature_data = audio_feature_data.append(new_features)
        if verbose:
            print('Done with tracks {} through {}'.format(i+1, i+50))
    
    return audio_feature_data
    
cp4_audio_features = get_audio_features(spotify, cp4_artist_song,verbose=True)    

cp4_audio_features.rename(columns={'id':'spotify_ID'}, inplace=True)        

cp4_artist_song = cp4_artist_song.merge(cp4_audio_features, how='left', 
                                        on='spotify_ID')

cp_song_data_four = cp_song_data_four.merge(cp4_artist_song, how='left',
                                            on=['artist','song'])

cp_song_data_four.to_csv('four_chord_songs.csv', index=False)

del cp_song_data_four
del cp4_artist_song
del cp4_audio_features


##################################
# Now repeat for three and five chord progressions.
##################################

# THREE CHORD PROGRESSIONS:

HT_AUTH_REQUEST_RESP = requests.request('POST',
                                        HT_AUTH_REQUEST_URL,
                                        json=HT_AUTH_REQUEST_BODY)

HT_AUTH_REQUEST_CONTENT = HT_AUTH_REQUEST_RESP.json()

ht_activation_key = 'Bearer ' + HT_AUTH_REQUEST_CONTENT['activkey']

ht_auth_header = {'Authorization': ht_activation_key}

client = requests.session()
client.headers = ht_auth_header

cp_song_data_three = get_cp_song_data(client, three_chord, verbose=1)

cp_song_data_three.song = cp_song_data_three.song.apply(lambda x: x.lower())
cp_song_data_three.artist = cp_song_data_three.artist.apply(lambda x: x.lower())
cp_song_data_three.section= cp_song_data_three.section.apply(lambda x: x.lower())


cp3_artist_song = cp_song_data_three[['artist', 'song']]
cp3_artist_song.drop_duplicates(inplace=True)
cp3_artist_song.sort_values(by=['artist', 'song'], inplace=True)
cp3_artist_song.reset_index(inplace=True, drop=True)

token = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                 client_secret=SPOTIFY_CLIENT_SECRET)

cache_token = token.get_access_token()

spotify = Spotify(cache_token)

get_track_ids(spotify, cp3_artist_song)

cp3_audio_features = get_audio_features(spotify, cp3_artist_song,verbose=True)    

cp3_audio_features.rename(columns={'id':'spotify_ID'}, inplace=True)        

cp3_artist_song = cp3_artist_song.merge(cp3_audio_features, how='left', 
                                        on='spotify_ID')

cp_song_data_three = cp_song_data_three.merge(cp3_artist_song, how='left',
                                            on=['artist','song'])

cp_song_data_three.to_csv('three_chord_songs.csv', index=False)

del cp_song_data_three
del cp3_artist_song
del cp3_audio_features

######################################

# FIVE CHORD PROGRESSIONS

HT_AUTH_REQUEST_RESP = requests.request('POST',
                                        HT_AUTH_REQUEST_URL,
                                        json=HT_AUTH_REQUEST_BODY)

HT_AUTH_REQUEST_CONTENT = HT_AUTH_REQUEST_RESP.json()

ht_activation_key = 'Bearer ' + HT_AUTH_REQUEST_CONTENT['activkey']

ht_auth_header = {'Authorization': ht_activation_key}

client = requests.session()
client.headers = ht_auth_header

cp_song_data_five = get_cp_song_data(client, five_chord, verbose=1)

cp_song_data_five.song = cp_song_data_five.song.apply(lambda x: x.lower())
cp_song_data_five.artist = cp_song_data_five.artist.apply(lambda x: x.lower())
cp_song_data_five.section= cp_song_data_five.section.apply(lambda x: x.lower())


cp5_artist_song = cp_song_data_five[['artist', 'song']]
cp5_artist_song.drop_duplicates(inplace=True)
cp5_artist_song.sort_values(by=['artist', 'song'], inplace=True)
cp5_artist_song.reset_index(inplace=True, drop=True)

token = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                 client_secret=SPOTIFY_CLIENT_SECRET)

cache_token = token.get_access_token()

spotify = Spotify(cache_token)

get_track_ids(spotify, cp5_artist_song)

cp5_audio_features = get_audio_features(spotify, cp5_artist_song,verbose=True)    

cp5_audio_features.rename(columns={'id':'spotify_ID'}, inplace=True)        

cp5_artist_song = cp5_artist_song.merge(cp5_audio_features, how='left', 
                                        on='spotify_ID')

cp_song_data_five = cp_song_data_five.merge(cp5_artist_song, how='left',
                                            on=['artist','song'])

cp_song_data_five.to_csv('five_chord_songs.csv', index=False)

del cp_song_data_five
del cp5_artist_song
del cp5_audio_features

###########################################

# Get genre information for all tracks

three = pd.read_csv('three_chord_songs.csv')
four = pd.read_csv('four_chord_songs.csv')
five = pd.read_csv('five_chord_songs.csv')

three['cp_length'] = 3
four['cp_length'] = 4
five['cp_length'] = 5

three_four_five = three.append(four).append(five).reset_index(drop=True)

def get_track_genres(client, track_ids, verbose=False):
    data = pd.DataFrame([], columns=['spotify_ID', 'genres'])
    for i in range(0, len(track_ids), 20):
        tids = track_ids[i:i+20]
        tracks = client.tracks(tids)['tracks']
        artist_ids = [track['artists'][0]['id'] for track in tracks]
        artists = client.artists(artist_ids)['artists']
        genres = [artist['genres'] for artist in artists]
        new_data = [{'spotify_ID':tid, 'genres':genre} for tid,genre in zip(tids, genres)]
        data = data.append(new_data).dropna()
        if verbose:
            print('Finished fetching genres for tids {} through {}.'.format(i+1, i+20))
            print('New data shape: {}'.format(data.shape))
            
    return data
        
token = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                 client_secret=SPOTIFY_CLIENT_SECRET)

cache_token = token.get_access_token()

spotify = Spotify(cache_token)

track_genres = get_track_genres(spotify, three_four_five.spotify_ID.dropna().unique(),
                                verbose=True)

three_four_five = three_four_five.merge(track_genres, how='left', on='spotify_ID')

three_four_five.to_csv('three_four_five.csv', index=False)

# If one chord progression is contained within another, we favor the longer.
def remove_redundant_cp(data, l1, l2):
    cp_l1 = data.loc[data.cp_length==l1,['cp', 'artist', 'song', 'section']]
    cp_l2 = data.loc[data.cp_length==l2, ['cp', 'artist', 'song', 'section']]
    
    for i, row in cp_l1.iterrows():
        cp = row['cp']
        artist=row['artist']
        song=row['song']
        section=row['section']
        if ((cp_l2.cp.apply(lambda x: cp in x))&((artist==cp_l2.artist)&\
             ((song==cp_l2.song)&(section==cp_l2.section)))).any():
            data.drop(i, inplace=True)

three_four_five_pruned = three_four_five.copy()

remove_redundant_cp(three_four_five_pruned, 3, 4)
remove_redundant_cp(three_four_five_pruned, 3, 5)    
remove_redundant_cp(three_four_five_pruned, 4, 5)

# Save the new 'pruned' datasets

three_four_five_pruned.to_csv('three_four_five_pruned.csv', index=False)

# Make dataset of cp/artist/song/section combinations which have spotify info

has_audio_data_pruned = three_four_five_pruned.dropna(subset=['spotify_ID'])

has_audio_data_pruned.to_csv('three_four_five_has_audio_pruned.csv', index=False)

has_audio_data_pruned.reset_index(drop=True, inplace=True)

####################################

# NOW FOR EDA

print(three_four_five.shape)

print(has_audio_data_pruned.shape)

# 12511 non-redundant records with audio data

print(has_audio_data_pruned.cp_length.value_counts())

# 9884 5-chord progressions, 1479 3-chord progressions, 1148 4-chord progressions

print(has_audio_data_pruned.cp.describe()) 

# 1018 unique chord progressions, 

print(has_audio_data_pruned.groupby('cp_length').apply(lambda x: x.cp.describe()))

# 68 unique 3-chord progressions, 197 unique 4-chord progressions, 753 unique
# 5-chord progressions

# Note: to reformat genres as lists after loading csv, run the following:

# has_audio_data_pruned.genres = has_audio_data_pruned.genres.apply(
#    lambda x: [g.strip("' ") for g in x.strip('[]').split(',')] if x!='[]' else np.nan)

# Get all genres
all_genres = {}

for genres in has_audio_data_pruned.genres.dropna():
    for g in genres:
        if g in all_genres.keys():
            all_genres[g]+=1
        else:
            all_genres[g]=1

all_genres = pd.Series(all_genres)

print('The 20 most popular genres are: \n{}'.format(all_genres.sort_values(ascending=False).head(20)))
"""
pop                 3016
rock                2499
dance pop           2483
pop rock            1589
modern rock         1511
post-teen pop       1393
edm                 1074
permanent wave       947
pop punk             940
album rock           930
folk-pop             915
mellow gold          810
indie rock           755
soft rock            739
classic rock         729
indie pop            721
alternative rock     696
post-grunge          685
hard rock            633
neo mellow           631
"""

# Only use cps with at least 5 observations:

cp_group_sizes = has_audio_data_pruned.groupby('cp').size()
cp_group_sizes.name='n'
cp_group_sizes = cp_group_sizes.reset_index()


has_audio_data_pruned = has_audio_data_pruned.merge(cp_group_sizes, on='cp')

has_5_obs = has_audio_data_pruned[has_audio_data_pruned.n>=5]

print('Still have {} unique chord_progressions.'.format(has_5_obs.cp.unique().shape))

print(has_5_obs.groupby('cp_length').apply(lambda x: x.cp.describe()))

"""
cp         count  unique        top  freq
cp_length                                
3           1473      66      4,5,1   104
4            932      93    6,4,1,5    29
5           9066     342  4,1,5,6,4   312
"""

all_genres = {}

for genres in has_5_obs.genres:
    for g in genres:
        if g in all_genres.keys():
            all_genres[g]+=1
        else:
            all_genres[g]=1

all_genres = pd.Series(all_genres)
print('The 20 most popular genres are: \n{}'.format(all_genres.sort_values(ascending=False).head(20)))
"""
The 20 most popular genres are: 
pop                 2820
dance pop           2306
rock                2280
pop rock            1495
modern rock         1366
post-teen pop       1308
edm                  972
pop punk             893
permanent wave       885
album rock           852
folk-pop             846
mellow gold          758
soft rock            688
classic rock         680
indie rock           670
indie pop            643
post-grunge          642
alternative rock     621
neo mellow           596
hard rock            567
"""

numeric_audio_features = ['danceability', 'energy', 'loudness', 
                           'acousticness', 'valence', 'tempo']

def all_cp_plot(data, features):
    
    num_plots = len(features)
    cols = int(np.ceil(num_plots/3))
    fig = plt.figure(figsize=(6*cols,9))
    fig.subplots_adjust(hspace=.5, wspace=.3)
    
    for i, feature in enumerate(features):
        ax = fig.add_subplot(3, cols, i+1)
        cp_feature_groups = data.groupby('cp')[feature].agg([np.mean, np.std])
        feature_sorted = cp_feature_groups.sort_values(by='mean')
        feature_sorted['mean'].plot(ax=ax)
        plt.fill_between(feature_sorted.index, 
                         feature_sorted['mean']-feature_sorted['std'],
                         feature_sorted['mean'] + feature_sorted['std'], 
                         color='orange', alpha=0.2)
        plt.xticks([],[])
        plt.ylabel(feature)
        ax.set_title('Mean {}'.format(feature))
    plt.show()

    
def cp_plot(cp, data, numeric_features=[], compare=False):
    cp_data = data[data.cp==cp]
    num_plots = len(numeric_features)
    cols = int(np.ceil(num_plots/3))
    fig = plt.figure(figsize=(6*cols,9))
    fig.subplots_adjust(hspace=.5, wspace=.3)
    for i, feature in enumerate(numeric_features):
        ax = fig.add_subplot(3, cols, i+1)
        sns.distplot(cp_data[feature], hist=False, ax=ax, label=cp)
        if compare:
            sns.distplot(data[feature], color='orange', hist=False, ax=ax,
                         label='All CPs')
        ax.set_title('Distribution of {} for {}'.format(feature, cp))
    plt.show()
        













