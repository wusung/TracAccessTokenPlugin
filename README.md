
Trac Personal Access Tokens Plugin
==================================

An personal access tokens plugin for the open source Trac project
(http://trac.edgewall.org/). This Trac plugin allows you to generate personal access token in Trac. 
This plugin also allow you to insert tickets with the generating key. 

See http://trac.edgewall.org/wiki/TracDev for more information about developing
a Trac plugin.


How it works
------------

Once your existing tickets/wiki documents are indexed in the backend you can
make requests using the *Advanced Search* form.  These searches will be handled
by the search backend you have configured in trac.ini.  When new documents or
tickets are added `upsert_document()` will be called on each search backend
to update the index immediately.


How to use
----------

```
curl -X POST -H "Content-Type: application/json" -H "Authorization: token 6d9ccb0856a527bf47a845c103d55191" -H "Cache-Control: no-cache" -H "Postman-Token: 1fb79357-1b3a-c2ee-df79-7bd873438d87" -d '{
  "summary": "Trac 是否可以接外部的 Search Engine",
  "description": "讓搜尋速度變快這點還蠻重要的...",
  "author": "bot",
  "reporter": "gslin",
  "owner": "wusugnpeng",
  "notify": "true",
  "cc": "tingwu"
}' "http://127.0.0.1:8001/test/api/tickets"
```


Limitation
----------
The API only allow the `TICKET_ADMIN` users to assign author and creation time. 


Project Status
--------------
Stable, and active.


Installation
------------

This assumes you already have a Trac environment setup.

1. Build and install the plugin
```
cd tracaccesstokenplugin
python setup.py bdist_egg
cp ./dist/tracaccesstoken-*.egg <trac_environment_home>/plugins
```

2. Configure your trac.ini (see the Configuration section below).

3. Restart the trac server. This will differ based on how you are running trac (apache, tracd, etc).

4. Create the new tables for the plugin.
```
python db_init.py <trac_environment_home>
```

That's it. You should see an Access Token menu in the your preference.



Configuration
-------------

In `trac.ini` you'll need to configure whichever search backend you're using.  If
you're using the default elasticsearch  backend, add something like this:

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

[screenshot]: https://raw.github.com/blampe/TracAdvancedSearchPlugin/gh-pages/example.png "Screenshot"
