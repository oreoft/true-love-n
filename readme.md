## 一、背景

满足自己需要定制化一个微信机器人，之前用的一直是查克大佬版本，然后fork出来修改。随着长时间的使用，有些自己特殊需求没有办法满足，在上面开发扩展性和稳定性都比较差。

最初查克提供的版本只是作为群聊天的机器人发布，后面我有一些定时提醒、at触发回调、接受三方回调消息等等需求，然后都往这个服务写，之前架构是底层dll注入到微信 -> rpc把消息传出来 -> 本地客户端应用。然后所有业务写到这个客户端应用上，我来数数它要承载的功能：

	1. 启动入口(需要拉起微信登陆)
	1. 接受伪装拦截发出来的rpc请求
	1. 序列化并且发送rpc请求，
	1. 起http服务器以及对应接受逻辑
	1. 起定时任务以及各类定时任务逻辑
	1. 处理业务(与大预言模型交互，爬一些数据然后清理返回， 等等)

服务是不支持热更新的，所以可能我只需要改一个定时任务的逻辑，为了生效这个改动，我每次都得重启整个服务和流程，而且服务越来越臃肿稳定性也很差，有时候可能是一个地方线程处理问题，导致程序卡主，然后机器人就容易丢消息。

所以我打算进行改造，目的是提高服务的稳定性，丢消息率降低到0%， 提升消息并行处理能力；增加服务扩展能力，提升后期维护开发成本。

## 二、架构流程

针对遇到的问题，提出对应的解决办法。查克大佬的sdk已经足够完善，并且社区也很活跃，所以底层依然保持查克大佬sdk

我把这部分 dll注入到微信-> rpc服务端收/转发消息 -> rpc客户端收/转发消息 保持不变，但除此之外不再做任何的事情，把这个成为base层，然后新增server层来专门处理业务逻辑。

![image-20240109181654205](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202401100816234.png)

## 三、设计目标

![image-20240109173537617](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202401100735733.png)

## 四、设计思路及折衷

1. 对于base层，配置都采用硬编码，把所有配置尽可能转移到server层，我希望base它比较薄，除非是大的需求否则它可以保持一年半载不需要重启。设计想法也非常简单，入口启动文件，http服务文件，robot操作底层sdk文件，基本上三个文件就搞定了。**并且这是内网服务，所有接口都不鉴权。**
   1. 入口文件启动robot程序，启动web服务器
   2. http服务器文件里面把以下接口暴露
      1. 发送文本消息
      2. 发送图片消息
      3. 获取当前登录所有联系人信息(包括群)
      4. 通过wxid查询昵称
   3. robot操作底层sdk文件最重要的就是把rpc发过来的消息进行http转发到server服务(做好异常处理，如果下游服务挂了，消息就直接丢了)
2. 对于server层，这部分相对来说可以好好设计，因为里面业务相对来说比较复杂，有抽象的空间。这个服务改动进行重启，也比较好，不会需要重启微信，启动速度也比较快，都是http的服务比较可控
   1. 所有消息过来，经过gateway，进行消息的过滤和转发，不同的消息走到不同的handler
      1. 先判断群消息还是私聊消息
         1. 如果是群消息
            1. 先看群是否在响应群里面
            2. 然后再看是否被at
         2. 如果非群聊消息
            1. 如果是文本消息，统一都进行回复
      2. 然后再进行判断是否是聊天消息，还是执行消息，还是查询消息
   2. 推送回调请求， 上面的接口是给base调的，这个接口是给公网调用的，往base推送消息
   3. 定时任务模块，定义成模块，在入口函数里面调用，然后保持一直运行。
