# automatic_sermon_uploader
This is a python script that allows automatic upload of a sermon video to vimeo and post it on wordpress including a audio track of the sermon.

The script scans a local directory for a video. When the video is available it parses the filename of the video and creates a title which is used for the vimeo title and wordpress post title.

The audio file is generated from the video. The audio file is uploaded to wordpress. The video is then uploaded to vimeo. When finished a wordpress post is created. It includes the embedded vimeo video and the playable/downloadable audio file.

After that the audio file gets deleted.

One use case is our church environment where we want to publish the weekly sermon on our wordpress homepage with the files coming from our file server.
