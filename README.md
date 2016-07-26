Trac Personal Access Tokens Plugin
==================================

An personal access tokens plugin for the open source Trac project
(http://trac.edgewall.org/). This Trac plugin allows you to generate personal access token in Trac. 
This plugin also allow you to insert tickets with the generating access tokens. 

See http://trac.edgewall.org/wiki/TracDev for more information about developing
a Trac plugin.


How to use
----------

1. Create your personal access key in trac Preference>Access Tokens. Press `New Token` button then copy the access token to clipboard with `Copy to clipboard` button.
![screenshot](https://raw.githubusercontent.com/wusung/TracAccessTokenPlugin/master/tracaccesstoken/htdocs/img/example.png "Screenshot")


2. Use the token in HTTP header. You can see the following codes.

```
curl -X POST -H "Content-Type: application/json" -H "Authorization: token ${access_token}" -H "Cache-Control: no-cache" -d '{
  "summary": "Trac 是否可以接外部的 Search Engine",
  "description": "讓搜尋速度變快這點還蠻重要的...",
  "reporter": "gslin",
  "owner": "wusugnpeng",
  "notify": "true",
  "cc": "tingwu"
}' "http://192.168.24.206/trac/api/tickets"

```


Project Status
--------------
Stable, and active.


Installation
------------

This assumes you already have a Trac environment setup.

1. Build and install the plugin
```
cd TracAccessTokenPlugin
python setup.py bdist_egg
cp ./dist/TracAccessTokenPlugin-*.egg <trac_environment_home>/plugins
```

2. Configure your trac.ini (see the Configuration section below).

3. Restart the trac server. This will differ based on how you are running trac (apache, tracd, etc).

4. Create the new tables for the plugin.
```
python db_init.py -c <trac_environment_home>
```

That's it. You should see an Access Tokens menu in the your preference.



Configuration
-------------

In `trac.ini` you can configure the menu name of access tokens plugin. If
you're changing the default menu name of the plugin, add something like this:

```
[access_token_plugin]
menu_label = Access Tokens
```

button_label is optional.


You'll also need to enable the components.

```
[components]
tracaccesstoken.web_ui.* = enabled
tracaccesstoken.api.* = enabled
```
