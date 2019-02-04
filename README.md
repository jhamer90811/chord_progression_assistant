# Description of datasets:

All datasets were produced using the [Hooktheory API](https://www.hooktheory.com/api/trends/docs) and the [Spotify API](https://developer.spotify.com/documentation/web-api/).

Given a chord progression, the Hooktheory database annotates all of its child progressions with the proportion of songs containing that child node. For example, of all songs containing the progression "I, IV, vi", 55% are followed by "V" and 14% are followed by "IV". Information about interpreting the Hooktheory chord notation can be found [here](http://forum.hooktheory.com/t/vizualitation-of-all-chord-progressions-kinda/164/2).

Chord progressions were pulled from the Hooktheory database as follows:
* First, all one length chord progressions (single chords) which were contained in at least %5 of the Hooktheory song database were pulled.
* Next, length two chord progressions were constructed by appending to each of the length one chord progressions any chord which comprises at least 5% of all songs containing the given length one progression. So for example, 15% of songs in the Hooktheory database begin with the "I" chord. Of chords starting with "I", 6% are followed by "ii", hence the length-two chord progression "I, ii" was pulled from the database.
* Continuing in this way, we extract all 3, 4, and 5-chord progressions which have at least a 5% chance of occuring given their parent progression. 

After the chord progressions were obtained, I used the Hooktheory API again to pull all songs associated with the pulled progressions. Each song item contained information about the song, artist, and section (chorus, verse, etc.) which contained the given progression.

Next, given the song/artist pairs pulled from the Hooktheory database, I used the Spotify API to query the Spotify track database to find tracks which match the song/artist pair. Of the songs for which a match was found, I then used the Spotify API again to pull detailed audio features for each track, and the genre information for the artists of the tracks. Detailed information about audio features can be found [here](https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/)

All of the following datasets were constructed by manipulating/cleaning the data pulled in the aforementioned manner.

## three_, four_, and five_chord_songs.csv

As the titles suggest, these contain all three/four/five chord progressions along with any song/artist/section information pulled from the Hooktheory database. Where possible, Spotify audio feature data is given. No genre information is given.

## three_four_five.csv

This is the concatenation of the three_, four_, five_chord_songs.csv datasets. Moreover, where possible genre information is given. The genres correspond to the artist of the song (though the song doesn't necessarily fit into each genre which describes a given artist).

## three_four_five_pruned.csv

Several three- and four-chord progressions are contained in progressions of a longer length. For example, "I, IV, I" is contained in "I, IV, I, V" which is itself contained in "I, IV, I, V, I". This dataset removes redundant chord progressions by favoring the longer progression. Thus in the example given, if a given song/artist/section combination contains both "I, IV, I" and "I, IV, I, V", the rows pertaining to "I, IV, I" are pruned from the dataset. Similarly, if the same song/artist/section combination contains "I, IV, I, V, I", then the four-chord progression is also pruned.

## three_four_five_has_audio_pruned.csv

This is a further refinement of three_four_five_pruned.csv which retains only those song/artist combinations for which Spotify information was successfully queried.
