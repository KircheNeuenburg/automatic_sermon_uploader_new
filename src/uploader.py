""" automatic_sermon_uploader """


def load_config(file_path):
    """ loads configuration from json file specified with path"""
    import json

    with open(file_path) as json_file:
        data = json.load(json_file)

    return data


def test_get_file_list(tmpdir):

    empty_list = list("")
    assert get_file_list("./", "mp3") == empty_list


def get_file_list(path, file_extension):
    """ searches all files in path for files matching the file extension """
    import glob

    try:
        if path.endswith('/'):
            path = path[:-1]

    file_list = glob.glob(path + "/*." + file_extension)

    except:
        file_list = []

    return file_list


def create_baptism_video_password(metadata):
    """ creates a password for video access"""

    return "taufe" + metadata["date"].strftime("%d%m%Y")


def convert_video_to_audio(file_path, video_extension, audio_extension):
    """ converts the video file to an audio file """
    import moviepy.editor as mp

    try:
    audio_path = file_path.replace("." + video_extension,
                                   "." + audio_extension)
    clip = mp.VideoFileClip(file_path).subclip(0)
    clip.audio.write_audiofile(audio_path, 44100, 2, 2000,
                                   None, "128k", None, False, False, False)
    except:
        audio_path = ''

    return audio_path


def get_sermon_metadata(file_path):
    """ extracts date, title and preacher out of filename """
    import re
    import datetime

    metadata = {"date": None, "title": None, "preacher": None}

    file_name = file_path.split("/")[-1]

    regex_match = re.match("(?P<date>[0-9]{4}-[0,1][0-9]-[0-3][0-9])_" +
                           "(?P<title>[\\W\\w]+)_(?P<preacher>[\\W\\w]+)" +
                           "[.][\\W\\w]+",
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


def get_baptism_metadata(file_path):
    """ extracts date out of filename """
    import re
    import datetime

    metadata = {"date": None}

    file_name = file_path.split("/")[-1]

    regex_match = re.match("(?P<date>[0-9]{4}-[0,1][0-9]-[0-3][0-9])_" +
                           "Taufe[.][\\W\\w]+",
                           file_name)

    if regex_match:
        date_raw = regex_match.group("date").split("-")

        metadata["date"] = datetime.date(int(date_raw[0]), int(date_raw[1]),
                                         int(date_raw[2]))
    else:
        metadata = None

    return metadata


def upload_sermon_to_peertube(config, video_path, metadata):
    """ uploads the video to vimeo using the credentials stored in config """
    import pt_upload
    options = dict()
    secret = dict()
    options['file'] = video_path
    options['name'] = metadata["title"] + " // " +  metadata["preacher"] +  " // Gottesdienst am " +   metadata["date"].strftime("%d.%m.%Y")
    options['language'] = "german"
    secret['peertube_url'] = config['peertube']['peertube_url']
    secret['client_id'] = config['peertube']['client_id']
    secret['username'] = config['peertube']['username']
    secret['password'] = config['peertube']['password']
    secret['client_secret'] = config['peertube']['client_secret']
    oauth = pt_upload.get_authenticated_service(secret)
    video_uri = pt_upload.upload_video(oauth, secret, options)
    print(video_uri)
    return video_uri


def upload_sermon_to_vimeo(config, video_path, metadata):
    """ uploads the video to vimeo using the credentials stored in config """
    import vimeo

    vimeo_handle = vimeo.VimeoClient(
        token=config["vimeo"]["token"],
        key=config["vimeo"]["key"],
        secret=config["vimeo"]["secret"])

    video_uri = vimeo_handle.upload(video_path)

    vimeo_handle.patch(video_uri, data={'name': metadata["title"] + " // " +
                                        metadata["preacher"] +
                                        " // Gottesdienst am " +
                                        metadata["date"].strftime("%d.%m.%Y"),
                                        'description': ''})
    video_uri = video_uri.replace("s", "")
    return video_uri


def upload_baptism_to_vimeo(config, video_path, metadata):
    """ uploads the video to vimeo using the credentials stored in config """
    import vimeo

    vimeo_handle = vimeo.VimeoClient(
        token=config["vimeo"]["token"],
        key=config["vimeo"]["key"],
        secret=config["vimeo"]["secret"])

    video_uri = vimeo_handle.upload(video_path)

    vimeo_handle.patch(video_uri, data={'name': "Zur Erinnerung " +
                                        "an die Taufe am " +
                                        metadata["date"].strftime("%d.%m.%Y"),
                                        'description': '',
                                        'privacy': {'view': 'password'},
                                        'password':
                                        create_baptism_video_password(metadata)
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
        config["wordpress"]["user"], config["wordpress"]["password"])

    audio_name = audio_path.split("/")[-1]

    audio_mime_type = mimetypes.guess_type(audio_path)
    # prepare metadata
    data = {
        'name': audio_name,
        'type': audio_mime_type, }

    # read the binary file and let the XMLRPC library encode it into base64
    with open(audio_path, 'rb') as audio_data:
        data['bits'] = xmlrpc_client.Binary(audio_data.read())

    response = wordpress_handle.call(media.UploadFile(data))

    return response['url']


def copy_audio_to_wordpress(config, audio_path):
    """moves the audio to wordpress using the wp path stored in config"""

    import shutil

    audio_name = audio_path.split("/")[-1]
    audio_url = config["wordpress"]["url"] + "/" + \
        config["wordpress"]["wp_audio_path"] + "/" + audio_name

    shutil.copy(audio_path, config["wordpress"]["local_audio_path"])

    return audio_url


def create_wordpress_post(config, video_url, audio_url, metadata):
    """ creates a wordpress post with the embedded video and Audio """
    import datetime
    from wordpress_xmlrpc import Client, WordPressPost
    from wordpress_xmlrpc.methods import posts

    wordpress_handle = Client(
        config["wordpress"]["url"] + "/xmlrpc.php",
        config["wordpress"]["user"], config["wordpress"]["password"])

    if video_url is not None:
        video_html = "<div>[iframe src=\"https://player.vimeo.com" + \
            video_url + "\" width=\"" + config["wordpress"]["video_width"] + \
            "\" height=\"" + config["wordpress"]["video_height"] + "\" \
            frameborder=\"0\" allowfullscreen=\"allowfullscreen\"]</div>"
    else:
        video_html = "<div> Es tut uns Leid, aus technischen Gr&uuml;nden gibt \
            es zu diesem Gottesdienst leider kein Video</div>"

    if audio_url is not None:
        download_html = "<a style=\"text-decoration:none; background-color:" +\
            config["wordpress"]["download_button_color"] +\
            "; border-radius:3px; padding:5px; color:#ffffff; \
            border-color:black; border:1px;\" href=\"" + audio_url +\
            "\" title=\"" + config["Wordpress"]["download_button_text"] + \
            "\" target=\"_blank\">" +\
            config["wordpress"]["download_button_text"] + "</a>"
        audio_html = "<div><h3>Audiopredigt:</h3><audio controls src=\"" + \
            audio_url + "\"></audio></div>"
    else:
        audio_html = "<div> Es tut uns Leid, aus technischen Gr&uuml;nden gibt \
            es zu diesem Gottesdienst leider keine Tonaufnahme</div>"
        download_html = ""

    if (video_url is None) and (audio_url is None):
        video_html = "<div> Es tut uns Leid, aus technischen Gr&uuml;nden gibt \
            es zu diesem Gottesdienst leider kein Video und keine Tonaufnahme\
            </div>"
        download_html = ""
        audio_html = ""

    date_time = datetime.datetime(
        metadata["date"].year, metadata["date"].month, metadata["date"].day,
        config["sermon_start_utc"])

    post = WordPressPost()
    post.title = metadata["title"] + " // " + metadata["preacher"]
    post.content = video_html + audio_html + download_html
    post.date = date_time
    post.terms_names = {
        'post_tag': [metadata["title"], metadata["preacher"]],
        'category': [config["wordpress"]["category"]],
        }
    post.post_status = 'publish'
    post.id = wordpress_handle.call(posts.NewPost(post))


def send_baptism_online_notification(config, video_url, metadata):
    """ send mail notification when baptism video was uploaded"""

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart()
    msg['From'] = config["mail"]["sender"]
    msg['To'] = ", ".join(config["mail"]["receivers"])
    msg['Subject'] = "Video der Taufe am " +\
                     metadata["date"].strftime("%d.%m.%Y")

    video_link = "https://vimeo.com/" + video_url.split("/")[-1]
    content = "Hallo,<br><br>das Video der Taufe am " +\
              metadata["date"].strftime("%d.%m.%Y") +\
              " gibt es unter folgenden Link:<br><a href=\"" + video_link +\
              "\">" + video_link + "</a><br>Passwort: " + \
              create_baptism_video_password(metadata) +\
              "<br><br>Bitte leitet das an die Tauffamilie(n) weiter. " +\
              "Vielen Dank!<br><br>" + config["mail"]["signature"]
    msg.attach(MIMEText(content, "html"))

    mailserver = smtplib.SMTP(config["mail"]["smtp_server"],
                              config["mail"]["smtp_port"])
    # identify ourselves to smtp gmail client
    mailserver.ehlo()
    # secure our email with tls encryption
    mailserver.starttls()
    # re-identify ourselves as an encrypted connection
    mailserver.ehlo()
    mailserver.login(config["mail"]["login"], config["mail"]["password"])

    config["mail"]["receivers"]
    mailserver.sendmail(config["mail"]["sender"],
                        config["mail"]["receivers"],
                        msg.as_string())

    mailserver.quit()


def main():
    """ here happens all the magic """
    import os
    import shutil

    config = load_config("./config.json")

    audio_list = get_file_list(
        config["search_path"], config["audio_file_extension"])
    video_list = get_file_list(
        config["search_path"], config["video_file_extension"])
    text_list = get_file_list(
        config["search_path"], config["text_file_extension"])

    for video in video_list:
        metadata = get_sermon_metadata(video)
        if metadata is not None:
            audio = convert_video_to_audio(
                video, config["video_file_extension"],
                config["audio_file_extension"])
            video_url = upload_sermon_to_peertube(config, video, metadata)
            audio_url = copy_audio_to_wordpress(config, audio)
            create_wordpress_post(config, video_url, audio_url, metadata)
            shutil.move(
                video, config["archive_path"] + "/" + video.split("/")[-1])
            os.remove(audio)
        else:
            metadata = get_baptism_metadata(video)
            if metadata is not None:
                video_url = upload_baptism_to_vimeo(config, video, metadata)
                send_baptism_online_notification(config, video_url, metadata)
                shutil.move(
                    video, config["archive_path"] + "/Taufe/" +
                    video.split("/")[-1])

    for audio in audio_list:
        metadata = get_sermon_metadata(audio)
        if metadata is not None:
            audio_url = copy_audio_to_wordpress(config, audio)
            create_wordpress_post(config, None, audio_url, metadata)
            shutil.move(
                audio, config["archive_path"] + "/" + audio.split("/")[-1])

    for text in text_list:
        metadata = get_sermon_metadata(text)
        if metadata is not None:
            create_wordpress_post(config, None, None, metadata)
            os.remove(text)

if __name__ == "__main__":
    main()
