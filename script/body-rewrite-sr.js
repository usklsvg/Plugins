const NAME = "body-rewrite";
const TITLE = "body-rewrite";
const $ = new Env(NAME);
// $argument =
//   '%5B%5B%22json-del%22%2C%5B%22a.b%5B1%5D%22%2C%22a.b%5B2%5D%22%5D%5D%2C%5B%22replace-regex%22%2C%5B%5B%22a%7Cb%7Cc%22%2C%22req%22%5D%5D%5D%5D'
let result = {};
!(async () => {
  if (typeof $argument == "undefined") throw new Error("$argument 不能为空");
  let actions;
  if (typeof $argument != "undefined") {
    if (!$argument) throw new Error("$argument 不能为空");
    try {
      actions = JSON.parse(decodeURIComponent($argument));
    } catch (e) {
      throw new Error("$argument 解析失败");
    }
    // $.log(JSON.stringify(actions, null, 2));
  }
  let shouldParseJSON = actions.find(([action]) => action.startsWith("json"));
  //   $.log(`shouldParseJSON: ${shouldParseJSON ? "true" : "false"}`);

  let body;
  if (typeof $response != "undefined") {
    body = $response.body;
  } else if (typeof $request != "undefined") {
    body = $request.body;
  } else {
    throw new Error("不为 请求 或 响应");
    // body = JSON.stringify({
    //   a: {
    //     b: ['c', 'd', 'f', 'g'],
    //   },
    // })
  }
  // $.log($.toStr(body))
  if (shouldParseJSON) {
    try {
      body = JSON.parse(body);
    } catch (e) {
      throw new Error("JSON 解析失败");
    }
  }

  for (let [action, items] of actions) {
    if (action === "json-del") {
      for (let item of items) {
        unset(body, item);
      }
    } else if (action === "json-add") {
      for (let item of items) {
        $.lodash_set(body, item[0], item[1]);
      }
    } else if (action === "json-replace") {
      for (let item of items) {
        if ($.lodash_get(body, item[0]) !== undefined) {
          $.lodash_set(body, item[0], item[1]);
        }
      }
    } else if (action === "replace-regex") {
      if (shouldParseJSON) {
        body = JSON.stringify(body);
      }
      for (let item of items) {
        body = body.replace(new RegExp(item[0], "g"), item[1]);
      }
      if (shouldParseJSON) {
        try {
          body = JSON.parse(body);
        } catch (e) {
          throw new Error("replace-regex 过程中 JSON 解析失败");
        }
      }
    }
  }

  result = {
    body: shouldParseJSON ? JSON.stringify(body) : body,
  };
})()
  .catch(async (e) => {
    $.logErr(e);
    $.logErr($.toStr(e));
    await notify(
      TITLE,
      "❌",
      `${$.lodash_get(e, "message") || $.lodash_get(e, "error") || e}`
    );
  })
  .finally(async () => {
    // $.log($.toStr(result))
    $.done(result);
  });
function parseJsonPath(_path) {
  const path = _path.trim();
  const output = [];
  const regex = /\.?([^\.\[\]]+)|\[(['"])(.*?)\2\]|\[(\d+)\]/g;
  let match;

  while ((match = regex.exec(path)) !== null) {
    if (match[1] !== undefined) {
      // 匹配点符号或初始键
      output.push(match[1]);
    } else if (match[3] !== undefined) {
      // 匹配带引号的括号表示法
      output.push(match[3]);
    } else if (match[4] !== undefined) {
      // 数组索引，转换为整数
      output.push(parseInt(match[4], 10));
    }
  }
  return output;
}
function unset(object, path) {
  if (object == null) {
    return true;
  }

  const paths = parseJsonPath(path);

  var current = object;
  for (var i = 0; i < paths.length - 1; i++) {
    var key = paths[i];
    if (!(key in current)) {
      return true;
    }
    current = current[key];
    if (current == null) {
      return true;
    }
  }

  var finalKey = paths[paths.length - 1];

  // 处理数组的情况
  if (Array.isArray(current)) {
    var index = parseInt(finalKey, 10);
    if (!isNaN(index)) {
      current.splice(index, 1);
      return true;
    }
  }

  // 处理对象的属性删除
  delete current[finalKey];
  return true;
}
// 通知
async function notify(title, subt, desc, opts) {
  $.msg(title, subt, desc, opts);
}

function Env(t, e) {
  class s {
    constructor(t) {
      this.env = t;
    }
    send(t, e = "GET") {
      t = "string" == typeof t ? { url: t } : t;
      let s = this.get;
      return (
        "POST" === e && (s = this.post),
        new Promise((e, r) => {
          s.call(this, t, (t, s, a) => {
            t ? r(t) : e(s);
          });
        })
      );
    }
    get(t) {
      return this.send.call(this.env, t);
    }
    post(t) {
      return this.send.call(this.env, t, "POST");
    }
  }
  return new (class {
    constructor(t, e) {
      (this.name = t),
        (this.http = new s(this)),
        (this.data = null),
        (this.dataFile = "box.dat"),
        (this.logs = []),
        (this.isMute = !1),
        (this.isMuteLog = !1),
        (this.isNeedRewrite = !1),
        (this.logSeparator = "\n"),
        (this.encoding = "utf-8"),
        Object.assign(this, e);
    }
    toObj(t, e = null) {
      try {
        return JSON.parse(t);
      } catch {
        return e;
      }
    }
    toStr(t, e = null) {
      try {
        return JSON.stringify(t);
      } catch {
        return e;
      }
    }
    getjson(t, e) {
      let s = e;
      const r = this.getdata(t);
      if (r)
        try {
          s = JSON.parse(this.getdata(t));
        } catch {}
      return s;
    }
    setjson(t, e) {
      try {
        return this.setdata(JSON.stringify(t), e);
      } catch {
        return !1;
      }
    }
    getScript(t) {
      return new Promise((e) => {
        this.get({ url: t }, (t, s, r) => e(r));
      });
    }
    runScript(t, e) {
      return new Promise((s) => {
        let r = this.getdata("@chavy_boxjs_userCfgs.httpapi");
        r = r ? r.replace(/\n/g, "").trim() : r;
        let a = this.getdata("@chavy_boxjs_userCfgs.httpapi_timeout");
        (a = a ? 1 * a : 20), (a = e && e.timeout ? e.timeout : a);
        const [o, i] = r.split("@"),
          n = {
            url: `http://${i}/v1/scripting/evaluate`,
            body: { script_text: t, mock_type: "cron", timeout: a },
            headers: { "X-Key": o, Accept: "*/*" },
            timeout: a,
          };
        this.post(n, (t, e, r) => s(r));
      }).catch((t) => this.logErr(t));
    }
    loaddata() {
      return {};
    }
    writedata() {}
    lodash_get(t, e, s) {
      const r = e.replace(/\[(\d+)\]/g, ".$1").split(".");
      let a = t;
      for (const t of r) if (((a = Object(a)[t]), void 0 === a)) return s;
      return a;
    }
    lodash_set(t, e, s) {
      return Object(t) !== t
        ? t
        : (Array.isArray(e) || (e = e.toString().match(/[^.[\]]+/g) || []),
          (e
            .slice(0, -1)
            .reduce(
              (t, s, r) =>
                Object(t[s]) === t[s]
                  ? t[s]
                  : (t[s] = Math.abs(e[r + 1]) >> 0 == +e[r + 1] ? [] : {}),
              t
            )[e[e.length - 1]] = s),
          t);
    }
    getdata(t) {
      let e = $persistentStore.read(t);
      if (/^@/.test(t)) {
        const [, s, r] = /^@(.*?)\.(.*?)$/.exec(t),
          a = s ? $persistentStore.read(s) : "";
        if (a)
          try {
            const t = JSON.parse(a);
            e = t ? this.lodash_get(t, r, "") : e;
          } catch (t) {
            e = "";
          }
      }
      return e;
    }
    setdata(t, e) {
      let s = !1;
      if (/^@/.test(e)) {
        const [, r, a] = /^@(.*?)\.(.*?)$/.exec(e),
          o = $persistentStore.read(r),
          i = r ? ("null" === o ? null : o || "{}") : "{}";
        try {
          const e = JSON.parse(i);
          this.lodash_set(e, a, t),
            (s = $persistentStore.write(JSON.stringify(e), r));
        } catch (e) {
          const o = {};
          this.lodash_set(o, a, t),
            (s = $persistentStore.write(JSON.stringify(o), r));
        }
      } else s = $persistentStore.write(t, e);
      return s;
    }
    initGotEnv(t) {
      (this.got = this.got ? this.got : require("got")),
        (this.cktough = this.cktough ? this.cktough : require("tough-cookie")),
        (this.ckjar = this.ckjar ? this.ckjar : new this.cktough.CookieJar()),
        t &&
          ((t.headers = t.headers ? t.headers : {}),
          void 0 === t.headers.Cookie &&
            void 0 === t.cookieJar &&
            (t.cookieJar = this.ckjar));
    }
    get(t, e = () => {}) {
      t.headers &&
        (delete t.headers["Content-Type"],
        delete t.headers["Content-Length"],
        delete t.headers["content-type"],
        delete t.headers["content-length"]),
        t.params && (t.url += "?" + this.queryStr(t.params));
      false &&
        this.isNeedRewrite &&
        ((t.headers = t.headers || {}),
        Object.assign(t.headers, { "X-Surge-Skip-Scripting": !1 })),
        $httpClient.get(t, (t, s, r) => {
          !t &&
            s &&
            ((s.body = r),
            (s.statusCode = s.status ? s.status : s.statusCode),
            (s.status = s.statusCode)),
            e(t, s, r);
        });
    }
    post(t, e = () => {}) {
      const s = t.method ? t.method.toLocaleLowerCase() : "post";
      t.body &&
        t.headers &&
        !t.headers["Content-Type"] &&
        !t.headers["content-type"] &&
        (t.headers["content-type"] = "application/x-www-form-urlencoded"),
        t.headers &&
          (delete t.headers["Content-Length"],
          delete t.headers["content-length"]);

      false &&
        this.isNeedRewrite &&
        ((t.headers = t.headers || {}),
        Object.assign(t.headers, { "X-Surge-Skip-Scripting": !1 })),
        $httpClient[s](t, (t, s, r) => {
          !t &&
            s &&
            ((s.body = r),
            (s.statusCode = s.status ? s.status : s.statusCode),
            (s.status = s.statusCode)),
            e(t, s, r);
        });
    }
    time(t, e = null) {
      const s = e ? new Date(e) : new Date();
      let r = {
        "M+": s.getMonth() + 1,
        "d+": s.getDate(),
        "H+": s.getHours(),
        "m+": s.getMinutes(),
        "s+": s.getSeconds(),
        "q+": Math.floor((s.getMonth() + 3) / 3),
        S: s.getMilliseconds(),
      };
      /(y+)/.test(t) &&
        (t = t.replace(
          RegExp.$1,
          (s.getFullYear() + "").substr(4 - RegExp.$1.length)
        ));
      for (let e in r)
        new RegExp("(" + e + ")").test(t) &&
          (t = t.replace(
            RegExp.$1,
            1 == RegExp.$1.length
              ? r[e]
              : ("00" + r[e]).substr(("" + r[e]).length)
          ));
      return t;
    }
    queryStr(t) {
      let e = "";
      for (const s in t) {
        let r = t[s];
        null != r &&
          "" !== r &&
          ("object" == typeof r && (r = JSON.stringify(r)),
          (e += `${s}=${r}&`));
      }
      return (e = e.substring(0, e.length - 1)), e;
    }
    msg(e = t, s = "", r = "", a) {
      const o = (t) => {
        switch (typeof t) {
          case void 0:
          case "string":
            return t;
          case "object": {
            let e = t.url || t.openUrl || t["open-url"];
            return { url: e };
          }
          default:
            return;
        }
      };
      if (!this.isMute) $notification.post(e, s, r, o(a));
      if (!this.isMuteLog) {
        let t = ["", "==============📣系统通知📣=============="];
        t.push(e),
          s && t.push(s),
          r && t.push(r),
          console.log(t.join("\n")),
          (this.logs = this.logs.concat(t));
      }
    }
    log(...t) {
      t.length > 0 && (this.logs = [...this.logs, ...t]),
        console.log(t.join(this.logSeparator));
    }
    logErr(t, e) {
      this.log("", `❗️${this.name}, 错误!`, t);
    }
    wait(t) {
      return new Promise((e) => setTimeout(e, t));
    }
    done(t = {}) {
      $done(t);
    }
  })(t, e);
}
