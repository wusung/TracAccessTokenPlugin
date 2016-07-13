
function jump_page(start_point_list, page, size) {
  var url = get_page_url(start_point_list, page, size);
  document.location.search = "?" + url;
  return false;
}

function get_page_url(start_point_list, page, size) {
	var form = $('#fullsearch');
	var query_string = form.serialize();
	var page = parseInt(page);
	query_string = query_string.replace(new RegExp("page=\\d+"), 'page='+page);
	// Join start points
	//query_string += '&' + $.param(start_point_list);
	query_string += '&PyElasticSearchBackEnd=' + (page * size);
    query_string += '&from=' + ((page-1)*size);

	return query_string;
}

function next_page(start_point_list) {
	var form = $('#fullsearch');
	var query_string = form.serialize();
	// Increase page count
	var page = parseInt(form.find('input[name=page]').val()) + 1;
	query_string = query_string.replace(new RegExp("page=\\d+"), 'page='+page);

	// Set start points
	query_string += '&' + $.param(start_point_list)

	document.location.search = '?' + query_string;
	return false;
}

function add_author_input(elem) {
	$(elem).parent('div').before(
		'<div><input type="text" name="author"/> ' +
		'<a href="#" onclick="return remove_author_input(this)">remove</a></div>'
	);
	return false;
}

function remove_author_input(elem) {
	$(elem).parent('div').remove();
	return false;
}

$(document).ready(function () {
	var clipboard = new Clipboard('#copy1', {
		target: document.querySelector('#clipboard')
	});

	$('#fullsearch input').change(function () {
		$('#fullsearch input[name="page"]').val(1);
	});
	var search = $('link[rel=search]');
	$(search).attr('href', $(search).attr('href').replace('search', 'advsearch'));

	var db = [];
	if ($('#tokens').val()) {
		db = JSON.parse($('#tokens').val());
	}

	$('#tokenGrid').jsGrid({
		width: "100%",
		editButton: true,
		deleteButton: true,
		modelSwitchButton: true,
		editing: true,
		data: db,
		deleteConfirm: function(item) {
			return "Are you sure?";
		},
		onItemDeleted: function(arg) {
			$("#tokenGrid").jsGrid("deleteItem", arg.item);
			$('#tokens').val(JSON.stringify(arg.data));
      $('#tokenGrid').trigger('reloadGrid');
			$.ajax({
				method: 'DELETE',
				contentType: "application/json",
				url: 'accesstoken?token_id=' + arg.item.id
			}).done(function(data) {
				console.log(data);
			});
    },
		onItemUpdated: function(arg) {
			$('#tokens').val(JSON.stringify(db));
			$.ajax({
				method: 'PUT',
				contentType: "application/json",
				url: 'accesstoken?token_id=' + arg.item.id,
				data: JSON.stringify({
					description: arg.item.description
				})
			}).done(function(data) {
				console.log(data);
			});
		},
		fields: [
      {
				name: "description",
				type: "text",
				title: "Description"
			},
			{
				name: "creationTime",
				type: "text",
				title: "Creation Time",
				editing: false
			},
			{
				type: "control"
			}
		]
	});

	$('#newToken').click(function() {
    var postData = {
			accessToken: Math.guid(),
			description: $('#tokenDesc').val(),
			creationTime: new Date().yyyy_mm_ddTHH_mm_ss_sssZ()
		};
		db.splice(0, 0, postData);
		$('#tokenGrid').jsGrid("reset");
		$('#tokens').val(JSON.stringify(db));
		$('#tokenDesc').val('');

		$.ajax({
			method: 'POST',
			contentType: "application/json",
			url: 'accesstoken',
			data: JSON.stringify(postData)
		}).done(function(data) {
			$("#clipboard").val(postData.accessToken);
		})
	});
});

function saveState(db) {
	$('#tokens').val(JSON.stringify(db));
}

Math.guid = function () {
	// return 'xxxxxxxxxxxx0xxxyxyxxxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
	// 	var string = Math.random() * 16 | 0, v = c === 'x' ? string : (string & 0x3 | 0x8);
	// 	return string.toString(16);
	// }).toUpperCase();

  return hat();
};

Date.prototype.yyyy_mm_ddTHH_mm_ss_sssZ = function() {
	var yyyy = this.getFullYear().toString();
	var mm = (this.getMonth() + 1).toString(); // getMonth() is zero-based
	var dd = this.getDate().toString();
	var hour = this.getHours().toString();
	var minutes = this.getMinutes().toString();
	var seconds = this.getSeconds().toString();
	var milliSeconds = this.getMilliseconds().toString();
	return yyyy + "-" + (mm[1] ? mm : "0" + mm[0]) + "-" + (dd[1] ? dd : "0" + dd[0])
			+ "T" + (hour[1] ? hour : "0" + hour[0])
			+ ":" + (minutes[1] ? minutes : "0" + minutes[0])
			+ ":" + (seconds[1] ? seconds : "0" + seconds[0])
			+ "." + milliSeconds
		    + "Z"; // padding
};
