function auto_complete(cm, b, c) {
  if(b.key.length == 1){
    if((b.key>='a' && b.key<='z')||(b.key>='A' && b.key<='Z')||(b.key=='.')){
        editor.showHint({completeSingle: false});
    }
  }
}

function sidebar_display(i){
    if (i){
        $('#sidebar').show();
        $('#right-content').css('width', '82%');
        $('#sidebar').css('width', '18%');
        $('#sidebar-btn').css('left', '18%');
        $("#sidebar-btn-li").removeClass('fa-caret-right');
        $("#sidebar-btn-li").addClass('fa-caret-left');
    }else{
        $('#sidebar-btn').tooltip('show');
        setTimeout(function(){
            $('#sidebar-btn').tooltip('hide');
            $('#sidebar-btn').tooltip('destroy');
            $('#sidebar-btn').removeAttr('title');
            $('#sidebar-btn').removeAttr('data-original-title');
        }, 1000);

        $('#sidebar').css('width', '0%');
        $('#sidebar').hide();
        $('#right-content').css('width', '100%');
        $('#sidebar-btn').css('left', '0px');
        $("#sidebar-btn-li").addClass('fa-caret-right');
        $("#sidebar-btn-li").removeClass('fa-caret-left');
    }
}

$(document).ready(function() {

    sidebar_display(parseInt(getCookie('sidebar_display')));
    editor = CodeMirror.fromTextArea(document.getElementById('id_sql'), {
      mode: 'text/x-mysql',
      lineNumbers: true,
      autofocus: true,
      hintOptions: { tables: {}, }
    });
    var doc = editor.getDoc();
    doc.setValue(localStorage.sql || '');

    if ($("#autocomplete").prop("checked")){
        editor.on('keyup', auto_complete);
    }
    $("#autocomplete").click(function() {
        if ($("#autocomplete").prop("checked")){
            editor.on('keyup', auto_complete);
        }else{
            editor.off('keyup', auto_complete);
        }
    });

    function get_keyworlds(){
        // 获取左侧table名
        $.ajax({
            url: table_list_url+$("#id_db").val(),
            type: "GET",
            success: function(data){
              //console.log(data);
              $(".nav-stacked").empty();
              if (data.success){
                for (var i=0; i<data.data.length;i++){
                  $(".nav-stacked").append('<li class="li-table-name"> <a href="#"><i class="fa fa-table"></i> '+data.data[i]+'</a> </li>');
                }
              }
            },
            error: function(xhr){
            }
        });

        // 获取自动补全的关键字
        $.ajax({
            url: keywords_url+$("#id_db").val(),
            type: "GET",
            success: function(data){
              //console.log(data);
              //hintOptions: { tables: {}, }
              editor.setOption('hintOptions', { tables: data, })
            },
            error: function(xhr){
            }
        });

    }

    get_keyworlds();
    $("#id_db").change(function(){
        get_keyworlds();
    });

    // 点击左侧表名添加表名
    $('#sidebar').on('click', 'li.li-table-name', function() {
      // console.log($(this).text());
      var doc = editor.getDoc();
      var cursor = doc.getCursor();
      doc.replaceRange($(this).text(), cursor)
      editor.focus();
    });

   $('#sidebar-btn').on('click', function(){
      if( $('#sidebar').is(':visible') ) {
          sidebar_display(0);
          setCookie('sidebar_display', 0);
      } else {
          sidebar_display(1);
          setCookie('sidebar_display', 1);
      }

    });

    function get_sql_result(is_explain){
        var doc = editor.getDoc();
        var all_sql = doc.getValue();
        localStorage.sql = all_sql;
        var sql = doc.getSelection();
        if (!sql){
            sql = all_sql;
        }
        if (!sql){
            iAlert("请填写查询的SQL");
            return false;
        }
        $("#result-spinner").show();
        $("#result-error").hide();
        $("#result-div").hide();
        $(".pagination").hide();
        $("#explain-btn").attr('disabled', 'disabled');
        $("#result-btn").attr('disabled', 'disabled');

        var url = $("#query_form").attr("action");

        var values = $("#query_form").serializeArray();
        for (index = 0; index < values.length; ++index) {
            if (values[index].name == "sql") {
                values[index].value = sql;
                break;
            }
        }
        if (is_explain){
           values.push({ name: "explain", value: 1 });
        }
        values = jQuery.param(values);
        // console.log(url);
        $.ajax({
            url: url,
            type: "POST",
            data: values,
            success: function(data){
                $("#result-spinner").hide();
                $("#explain-btn").removeAttr('disabled');
                $("#result-btn").removeAttr('disabled');
                // console.log(data);
                // center
                if (data.error){
                    $("#result-error").text(data.error);
                    $("#result-error").show();
                    $("#result-div").hide();
                }else{
                    $("#result-time").text(data.time.toFixed(2));
                    $("#result-count").text(data.count);
                    $("#result-keys").empty();
                    for (var i=0; i<data.keys.length; i++){
                        $("#result-keys").append('<td>'+escapeHtml(data.keys[i])+'</td>');
                    }
                    $("#result-data").empty();
                    for (var i=0; i<data.data.length; i++){
                        var row = data.data[i];
                        var result_data = '<tr>';
                        for (var j=0; j<row.length; j++){
                          result_data += '<td>'+escapeHtml(row[j])+'</td>';
                        }
                        $("#result-data").append(result_data += '/<tr>');
                    }
                    if (data.have_pagination){
                        $(".pagination").show();
                        var pageid = $('[name="page"]').val();
                        $(".pagination li").removeClass('active')
                        $("#page"+pageid).addClass('active')
                    }
                    $("#result-div").show();
                }
            },
            error: function(xhr){
                if (xhr.status==404){
                    iAlert("该记录不存在或被删除!");
                }else if(xhr.status == 403){
                    iAlert("没有权限!");
                }else if(xhr.status == 500){
                    iAlert("系统错误!");
                }
            }
        });

    }
   $('.page_id').on('click', function(e){
        e.preventDefault();
        var page = $(this).attr('data-pageid');
        $('[name="page"]').val(page);
        get_sql_result();
    });

   // 只提交选择的数据
   $('#result-btn').on('click', function(e){
        e.preventDefault();
        $('[name="page"]').val(1);
        get_sql_result(is_explain=false);
        return false;
    });
   $('#explain-btn').on('click', function(e){
        e.preventDefault();
        $('[name="page"]').val(1);
        get_sql_result(is_explain=true);
        return false;
    });




});
