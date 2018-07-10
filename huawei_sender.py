#coding:utf8
import requests
import redis
import json
import time
import logging
appPkgName = ''
app_id = ''
secret = ''
send_url = 'https://api.push.hicloud.com/pushsend.do'
send_url += '?nsp_ctx=%7b%22ver%22%3a%221%22%2c+%22appId%22%3a%22{appid}%22%7d'.format(appid=appid)

class HuweiMsg(object):
    def __init__(self,appid=appid,secret=secret):
        self.appid= appid
        self.secret = secret

    def _get_token(self):
        token = redis.get("huawei_push_access_token")
        if not token:
            token = self._require_token()
        return token

    @staticmethod
    def _make_post(url,data):
        try:
            res = requests.post(url, data=data,timeout=3)
            if res.status_code == 200:
                res_data = json.loads(res.content)
                return True, res_data
        except Exception as e:
            return False,e
        return False,''

    def _require_token(self):
        token_url = 'https://login.cloud.huawei.com/oauth2/v2/token'
        token_data =  {'grant_type':'client_credentials',
                       'client_secret':self.secret,
                       'client_id':self.appid}
        ok,data = self._make_post(token_url,token_data)
        if not ok:
            logging.error(data)
            raise ValueError
        access_token = data.get('access_token','')
        expires_in = data.get('expires_in','')
        redis.set("huawei_push_access_token",access_token,ex=int(expires_in))
        return access_token

    def send(self,msg,title,cid,extras={},through=0):
        if not isinstance(extras,dict):
            raise ValueError
        if not cid:
            raise ValueError
        if not title:
            title = '默认title'
        self.title = title
        self.msg = msg
        self.cid=cid
        self.extra = extras
        self.through = through
        self._build_push_data()
        return self._push()


    def _push(self):
        ok, data = self._make_post(send_url, self.push_data)
        if not ok:
            logging.error(data)
        if data.get("code") == '80000000':
            return True
        return False

    def send_cid(self,cid):
        self.push_data.update({{'device_token_list':json.dumps(cid)}})
        self._push()

    def _build_cid(self):
        if not isinstance(self.cid,list):
            msg_dict = {'device_token_list': json.dumps([str(self.cid)])}
        else:
            cid_length = len(self.cid)
            if cid_length>1000:
                for i in xrange(0,cid_length,1000):
                    self.send_cid(cid= map(str,self.cid[i:i+1000]))
            else:
                msg_dict = {'device_token_list':json.dumps(self.cid)}
        self.push_data.update(msg_dict)

    def _build_pay_load(self):
        self._build_pay_msg()
        hps = {"msg":self.pay_msg,'ext':{"customize":[self.extra]}}
        self.push_data.update({'payload':json.dumps({"hps":hps})})

    def _build_pay_msg(self):
        body = {"title":self.title,"content":self.msg}
        if self.through :
            body.update(self.extra)
        self.pay_msg = {"body": body}
        self._build_througt()


    def _build_push_data(self):
        self.push_data = {'access_token': self._get_token(), 'nsp_svc': 'openpush.message.api.send',
                     'nsp_ts': int(time.time()), }
        self._build_cid()
        self._build_pay_load()

    def _build_througt(self):
        if self.through:
            type_value = 1
        else:
            type_value = 3
            self.pay_msg.update({
                'action': {'type': 3, 'param': {'appPkgName': appPkgName}}})
        self.pay_msg.update({"type":type_value})


if __name__ == '__main__':
    test_cid = u'your client cid'
    l = HuweiMsg().send
    ext = {"url":"www.baidu.com","desc":"extra"}
    print l(msg="test",title=None,cid=test_cid,through=0,extras=ext)
