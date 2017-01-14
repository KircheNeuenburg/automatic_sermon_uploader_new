# automatic_upload_yt_wp
This is a python script that allows automatic upload of a video to youtube and post it on wordpress.

The script scans a webdav directory for a video and a corresponding audio file.
When the video and audio is available it parses the filename of the audio and creates a title which is used for the youtube title and wordpress post title.

The video is then uploaded to youtube. When finished a wordpress post is created. It includes the embedded youtube video and the playable/downloadable audio file.

After that the files are deleted.

One use case is our church environment where we want to publish the weekly sermon on our wordpress homepage with the files coming from our nextcloud server.
