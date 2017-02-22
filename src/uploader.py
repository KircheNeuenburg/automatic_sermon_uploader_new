""" automatic_sermon_uploader """


def load_config(file_path):
    """ loads configuration from json file specified with path"""
    import json

    with open(file_path) as json_file:
        data = json.load(json_file)

    return data


def get_file_list(path, file_extension):
    """ searches all files in path for files matching the file extension """
    import glob

    file_list = glob.glob(path + "/*." + file_extension)
    return file_list


def convert_video_to_audio(file_path, video_extension, audio_extension):
    """ converts the video file to an audio file """
    import moviepy.editor as mp

    audio_path = file_path.replace("." + video_extension,
                                   "." + audio_extension)
    clip = mp.VideoFileClip(file_path).subclip(0)
    clip.audio.write_audiofile(audio_path)
    return audio_path


def get_sermon_metadata(file_path):
    """ extracts date, title and preacher out of filename """
    import re
    import datetime

    metadata = {"date": None, "title": None, "preacher": None}

    file_name = file_path.split("/")[-1]

    regex_match = re.match(
                            r"""(?P<date>[0-9]{4}-[0,1][0-9]-[0-3][0-9])_(?P<tit
                            le>[\W\w]+)_(?P<preacher>[\W\w]+)[.][\W\w]+""",
                            file_name)

    if regex_match:
        date_raw = regex_match.group("date").split("-")

        metadata["date"] = datetime.date(int(date_raw[0]), int(date_raw[1]),
                                         int(date_raw[2]))
        metadata["title"] = regex_match.group("title")
        metadata["preacher"] = regex_match.group("preacher")
    else:
        metadata = None

    return metadata


def upload_video_to_vimeo(config, video_path, metadata):
    """ uploads the video to vimeo using the credentials stored in config """
    import vimeo

    vimeo_handle = vimeo.VimeoClient(
        token=config["vimeo"]["token"],
        key=config["vimeo"]["key"],
        secret=config["vimeo"]["secret"])

    video_uri = vimeo_handle.upload(video_path)

    vimeo_handle.patch(
        video_uri,
        data={
            'name': metadata["title"] + " // " + metadata["preacher"] +
            " // Gottesdienst am " + metadata["date"].strftime("%d.%m.%Y"),
            'description': ''
        })
    video_uri = video_uri.replace("s", "")
    return video_uri


def upload_audio_to_wordpress(config, audio_path):
    """uploads the audio to wordpress using the credentials stored in config"""
    import mimetypes
    from wordpress_xmlrpc import Client
    from wordpress_xmlrpc.compat import xmlrpc_client
    from wordpress_xmlrpc.methods import media

    wordpress_handle = Client(
        config["wordpress"]["url"] + "/xmlrpc.php",
        config["wordpress"]["user"], config["wordpress"]["password"]
    )

    audio_name = audio_path.split("/")[-1]

    audio_mime_type = mimetypes.guess_type(audio_path)
    # prepare metadata
    data = {
        'name': audio_name,
        'type': audio_mime_type,
        }

    # read the binary file and let the XMLRPC library encode it into base64
    with open(audio_path, 'rb') as audio_data:
        data['bits'] = xmlrpc_client.Binary(audio_data.read())

    response = wordpress_handle.call(media.UploadFile(data))

    return response['url']


def create_wordpress_post(config, video_url, audio_url, metadata):
    """ creates a wordpress post with the embedded video and Audio """
    import datetime
    from wordpress_xmlrpc import Client, WordPressPost
    from wordpress_xmlrpc.methods import posts
    from wordpress_xmlrpc.methods import taxonomies

    wordpress_handle = Client(
        config["wordpress"]["url"] + "/xmlrpc.php",
        config["wordpress"]["user"], config["wordpress"]["password"]
    )

    category = wordpress_handle.call(
        taxonomies.GetTerm('category', config["wordpress"]["category_id"])
    )

    if video_url is not None:
        video_html = "<div>[iframe src=\"https://player.vimeo.com" +\
            video_url + "\" width=\"" + config["wordpress"]["video_width"] + \
            "\" height=\"" + config["wordpress"]["video_height"] + "\" frameborder=\"0\" \
            allowfullscreen=\"allowfullscreen\"]</div>"
    else:
        video_html = "<div> Es tut uns Leid, aus Technischen Gr&uuml;nden gibt es zu \
            diesem Gottesdienst leider kein Video</div>"

    if audio_url is not None:
        download_html = "<a style=\"text-decoration:none; background-color:\
            #0076b3; border-radius:3px; padding:5px; color:#ffffff; \
            border-color:black; border:1px;\"\ href=\"" + audio_url + "\" \
            title=\"Download als MP3\" target=\"_blank\">Download als MP3</a>"
        audio_html = "<div><h3>Audiopredigt:</h3><audio controls src=\"" + \
            audio_url + "\"></audio></div>"
    else:
        audio_html = "<div> Es tut uns Leid, aus Technischen Gr&uuml;nden gibt es zu \
            diesem Gottesdienst leider keine Tonaufnahme</div>"
        download_html = ""

    if (video_url is None) and (audio_url is None):
        video_html = "<div> Es tut uns Leid, aus Technischen Gr&uuml;nden gibt es zu \
            diesem Gottesdienst leider kein Video und keine Tonaufnahme</div>"
        download_html = ""
        audio_html = ""

    date_time = datetime.datetime(
        metadata["date"].year, metadata["date"].month, metadata["date"].day,
        config["sermon_start_utc"]
    )

    post = WordPressPost()
    post.title = metadata["title"] + " // " + metadata["preacher"]
    post.content = video_html + audio_html + download_html
    post.date = date_time
    post.terms.append(category)
    # whoops, I forgot to publish it!
    # post.post_status = 'publish'
    post.id = wordpress_handle.call(posts.NewPost(post))


def main():
    """ here happens all the magic """
    import os

    print("Load Config")
    config = load_config("./config.json")

    print("Check for new files")
    audio_list = get_file_list(
        config["search_path"], config["audio_file_extension"]
    )
    video_list = get_file_list(
        config["search_path"], config["video_file_extension"]
    )
    text_list = get_file_list(
        config["search_path"], config["text_file_extension"]
    )

    for video in video_list:
        print("Process Video")
        metadata = get_sermon_metadata(video)
        if metadata is not None:
            print("Convert Audio")
            audio = convert_video_to_audio(
                video, config["video_file_extension"],
                config["audio_file_extension"]
            )
            print("Upload Video")
            video_url = upload_video_to_vimeo(config, video, metadata)
            print("Upload Audio")
            audio_url = upload_audio_to_wordpress(config, audio)
            print("Create Wordpress Post")
            create_wordpress_post(config, video_url, audio_url, metadata)
            os.remove(audio)

    for audio in audio_list:
        print("Process Audio")
        metadata = get_sermon_metadata(audio)
        if metadata is not None:
            print("Upload Audio")
            audio_url = upload_audio_to_wordpress(config, audio)
            print("Create Wordpress Post")
            create_wordpress_post(config, None, audio_url, metadata)
            os.remove(audio)

    for text in text_list:
        print("Process Text")
        metadata = get_sermon_metadata(text)
        if metadata is not None:
            print("Create Wordpress Post")
            create_wordpress_post(config, None, None, metadata)

if __name__ == "__main__":
    main()
