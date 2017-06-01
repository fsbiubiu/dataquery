/**
 * 提示框
 *      msg         提示的消息
 *      cls         提示的类
 *      hide_reload 隐藏后是否刷新页面
 */
var iAlert = function(msg, cls, hide_reload){
    $("#ialert-modal .modal-body").html('<p class="'+ (cls || "") + '">' + msg + '</p>');
    $("#ialert-modal").modal("show");
    if (hide_reload){
        $("#ialert-modal").on('hidden', function () {
            setTimeout("location.reload();", 500);
            $("#ialert-modal").off('hidden');
        });
    }
};

/**
  确认框
       options:
                msg         提示信息
                title       提示标题
                html        Body HTML 如果提供此参数则忽略 msg 
                show_footer 显示底部按钮, 默认: true
                cancel_txt  取消按钮文本, 默认: 取消
                confirm_txt 确认俺就文本, 默认: 确定
                cancel_cb   取消回调函数
                confirm_cb  确认回调函数
                shown_cb    悬浮框加载完成回调函数
 */
var iConfirm = function(options){
    if (options.html){
        $("#iconfirm-modal .modal-body").html(options.html);
        $("#iconfirm-modal .modal-dialog").removeClass("modal-sm");
        $("#iconfirm-modal .modal-dialog").addClass("modal-lg");
    }else{
        $("#iconfirm-modal .modal-dialog").removeClass("modal-lg");
        $("#iconfirm-modal .modal-dialog").addClass("modal-sm");
        $("#iconfirm-modal .modal-body").html('<p>' + options.msg + '</p>');
    }

    $("#iconfirm-modal .modal-title").html(options.title || "&nbsp;");

    if (options.show_footer !== undefined && options.show_footer === false){
        $("#iconfirm-modal .modal-footer").hide()
        if (options.max_height !== undefined || options.max_height === true){
            $("#iconfirm-modal .modal-dialog .modal-body").addClass("iconfirm-modal-max-height");
        }
    }else{
        $("#iconfirm-modal .modal-dialog .modal-body").removeClass("iconfirm-modal-max-height");
        $("#iconfirm-modal .modal-footer").show()
        $("#iconfirm-modal .modal-footer #iconfirm-cancel").html(options.cancel_txt || "取消");
        $("#iconfirm-modal .modal-footer #iconfirm-confirm").html(options.confirm_txt || "确定");

        var cb_called = false;

        $("#iconfirm-modal .modal-footer #iconfirm-confirm").click(function(){
            $(this).unbind();
            if (options.confirm_cb){
                options.confirm_cb()
                cb_called = true;
            }
        });

        $("#iconfirm-modal").on("hide.bs.modal", function(e){
            if (options.cancel_cb && !cb_called){
                options.cancel_cb()
                cb_called = true;
            }
            $("#iconfirm-modal .modal-footer #iconfirm-confirm").unbind("click");
            $("#iconfirm-modal").off("hide.bs.modal");
        });

        $("#iconfirm-modal").on("shown.bs.modal", function(e){
            // 悬浮框加载完成
            if (options.shown_cb){
                options.shown_cb();
            } 
            $("#iconfirm-modal").off("shown.bs.modal");
        });
    }

    $("#iconfirm-modal").modal('show');
};


function getCookie(sName){
  var aCookie=document.cookie.split("; ");
  for(var i=0;i<aCookie.length;i++){
    var aCrumb=aCookie[i].split("=");if(sName==aCrumb[0])
    return(aCrumb[1]);
  }
  return null;
}

function setCookie(c_name, value, exdays) {
    var exdate = new Date();
    exdate.setDate(exdate.getDate() + exdays);
    var c_value = escape(value) + ((exdays == null) ? "" : "; expires=" + exdate.toUTCString());
    document.cookie = c_name + "=" + c_value;
}


function escapeHtml(text) {
  // 用text比较好
  if (!text){
      return text;
  }
  if (typeof text == "string" ){
      var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      };
      return text.replace(/[&<>"']/g, function(m) { return map[m]; });
  }else{
      return text;
  }
}
