import json
import requests
import asyncio

def get_token():
    ak = "HPUAMPZVPMJCPUMPOKKT"
    sk = "t6IZR8B1bPHlElFNrGE4NvG51qVkJUC8siUqJkUB"

    # username = "hid_8grsc5xuwj545vw"
    # password = "z13846934374"
    domainname = "hid_8grsc5xuwj545vw"
    username = "iamuser"
    password = "x14789970190"
    userid = "e31a4af3853c478e8b7233ab51d9cdd1"

    domain = "cn-north-4"
    projectid = "8d57005a2d494493b5d91bf675a13bad"
    
    url = "https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens"
    headers = {
        "ContentType":"application/json;charset=utf8"
    }
    body = {
    "auth": {
        "identity": {
            "methods": [
                "password"
            ],
            "password": {
                "user": {
                    "domain": {
                        "name": domainname
                    },
                    "name": username,
                    "password": password
                }
            }
        },
        "scope": {
            "project": {
                "name": domain
            }
        }
    }
}
    data = json.dumps(body)
    # print(data)
    resp = requests.post(url, headers = headers, data = data,)
    token = resp.headers["x-subject-token"]
    # print(token)
    return token

async def predict(file_path, token):
    # v001
    # url = "https://infer-modelarts-cn-north-4.modelarts-infer.com/v1/infers/b7fc00a1-939b-4c9d-abe6-aff39ff0ef13"
    # v002
    url = "https://infer-modelarts-cn-north-4.modelarts-infer.com/v1/infers/c4ba48d3-ab32-4e28-83e6-85472a4c1413"
    # Send request.
    print("正在预测结果")
    headers = {
        'X-Auth-Token': token
    }
    files = {
        'images': open(file_path, 'rb')
    }
    resp = requests.post(url, headers=headers, files=files)

    # Print result.
    print(resp.status_code)
    scores = json.loads(resp.text)["scores"]
    print(scores)
    return scores[0][1], scores[0][0]


if __name__ == "__main__":
    # example
    token = get_token()
    predict("./test.jpg", token)