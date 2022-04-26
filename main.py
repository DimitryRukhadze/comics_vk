import requests
import os
import random
import shutil
import logging


from dotenv import load_dotenv


def get_comic_quantity():

    last_comic_url = "https://xkcd.com/info.0.json"
    last_comic_response = requests.get(last_comic_url)
    last_comic_response.raise_for_status()
    last_comic_info = last_comic_response.json()

    return last_comic_info['num']


def download_random_comic(comics_folder):

    comics_quantity = get_comic_quantity()

    rand_comic_num = random.randint(1, comics_quantity)
    rand_comic_data_url = f"https://xkcd.com/{rand_comic_num}/info.0.json"

    rand_comic_response = requests.get(rand_comic_data_url)
    rand_comic_response.raise_for_status()

    rand_comic_info = rand_comic_response.json()
    rand_comic_img_url = rand_comic_info['img']
    rand_comic_title = rand_comic_info['safe_title']
    rand_comic_comment = rand_comic_info['alt']

    img_extension = os.path.splitext(rand_comic_img_url)[-1]

    comic_img = requests.get(rand_comic_img_url)
    comic_img.raise_for_status()

    rand_comic_path = os.path.join(
        comics_folder,
        f'{rand_comic_title}{img_extension}'
        )
    with open(rand_comic_path, 'wb') as comic_file:
        comic_file.write(comic_img.content)

    return rand_comic_path, rand_comic_comment


def make_vk_request(vk_api_method, vk_token, vk_api, other_request_params=''):

    vk_api_url = f'https://api.vk.com/method/{vk_api_method}'
    data = {
        'access_token': vk_token,
        'v': vk_api
    }
    if other_request_params:
        data.update(other_request_params)

    response = requests.post(vk_api_url, data=data)
    response.raise_for_status()

    decoded_response = response.json()
    if 'error' not in decoded_response:
        return decoded_response
    logging.warning(
        f'В результате запроса произошла ошибка: {decoded_response["error"]["error_msg"]}'
    )


def upload_photo_to_server(upload_server_url, file_path):

    with open(file_path, 'rb') as comic_for_upload:
        files = {
            'photo': comic_for_upload,
        }
        upload_response = requests.post(upload_server_url, files=files)
    upload_response.raise_for_status()
    decoded_response = upload_response.json()

    return decoded_response['server'], decoded_response['photo'], decoded_response['hash']


if __name__ == '__main__':

    load_dotenv()

    logging.basicConfig(format="%(process)d %(levelname)s %(message)s %(asctime)s")

    vk_access_token = os.environ.get('VK_ACCESS_TOKEN')
    vk_api_version = os.environ.get('VK_API_VERSION')
    group_id = os.environ.get('USER_GROUP_ID')

    img_folder = os.environ.get('TEMP_IMG_FOLDER')
    os.makedirs(img_folder, exist_ok=True)

    comic_img_path, comic_text = download_random_comic(img_folder)

    try:
        photo_upload_data = make_vk_request(
            'photos.getWallUploadServer',
            vk_access_token,
            vk_api_version
            )
        comic_upload_url = photo_upload_data['response']['upload_url']

        upload_server, upload_photo, upload_hash = upload_photo_to_server(
            comic_upload_url,
            comic_img_path
        )

        save_params = {
            'server': upload_server,
            'photo': upload_photo,
            'hash': upload_hash
        }
        save_comic_to_post = make_vk_request(
            'photos.saveWallPhoto',
            vk_access_token,
            vk_api_version,
            other_request_params=save_params
        )
        photo_id = save_comic_to_post['response'][0]['id']
        photo_owner_id = save_comic_to_post['response'][0]['owner_id']

        post_comic_params = {
            'owner_id': f'-{group_id}',
            'from_group': 1,
            'attachments': f'photo{photo_owner_id}_{photo_id}',
            'message': comic_text,
        }

        post_comic = make_vk_request(
            'wall.post',
            vk_access_token,
            vk_api_version,
            other_request_params=post_comic_params
        )
    except requests.HTTPError:
        raise

    finally:
        shutil.rmtree(img_folder)
