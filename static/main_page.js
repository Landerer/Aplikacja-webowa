
function initDraw(canvas) {
    var mouse = {
        x: 0,
        y: 0,
        startX: 0,
        startY: 0
    };
    function setMousePosition(e) {
        var ev = e || window.event; //Moz || IE
        if (ev.pageX) { //Moz
            mouse.x = ev.pageX + window.pageXOffset;
            mouse.y = ev.pageY + window.pageYOffset;
        } else if (ev.clientX) { //IE
            mouse.x = ev.clientX + document.body.scrollLeft;
            mouse.y = ev.clientY + document.body.scrollTop;
        }
    };

    var element = null;
    canvas.onmousemove = function (e) {
        setMousePosition(e);
        if (element !== null) {
            element.style.width = Math.abs(mouse.x - mouse.startX) + 'px';
            element.style.height = Math.abs(mouse.y - mouse.startY) + 'px';
            element.style.left = (mouse.x - mouse.startX < 0) ? mouse.x + 'px' : mouse.startX + 'px';
            element.style.top = (mouse.y - mouse.startY < 0) ? mouse.y + 'px' : mouse.startY + 'px';
        }
    }

    canvas.onclick = function (e) {
        if (element !== null) {
            console.log("finsihed.")
            let ajax_options = {
                type: 'POST',
                url: 'images/7/descriptions/' + element.id,
                accepts: 'application/json',
                dataType: 'json',
                data: {
                    'x': mouse.startX,
                    'y': mouse.startY,
                    'width': mouse.x - mouse.startX,
                    'height': mouse.y - mouse.startY
                }
            };
            var ready_element = element;
            $.ajax(ajax_options)
                .done(function (data) {
                    ready_element.style.border = "3px solid green";
                })
            element = null;
            canvas.style.cursor = "default";
        } else {
            var descr_id = $('#canvas .rectangle').length
            console.log("begun.");
            mouse.startX = mouse.x;
            mouse.startY = mouse.y;
            element = document.createElement('div');
            element.id = descr_id;
            element.className = 'rectangle'
            element.style.left = mouse.x + 'px';
            element.style.top = mouse.y + 'px';
            canvas.appendChild(element)
            canvas.style.cursor = "crosshair";
        }
    }
}

function clear_descriptions() {
    var confirmation = confirm("Czy na pewno chcesz usunąć wszystkie opisy obrazu?");
    if (confirmation) {
        $('#canvas .rectangle').remove();
    }
}

function cancel() {
    var confirmation = confirm("Czy na pewno chcesz usunąć ostatni opis?");
    if (confirmation) {
        $('#canvas .rectangle:last-child').remove();
    }
}

function save() {
    document.getElementById("canvasimg").style.border = "2px solid";
    var dataURL = canvas.toDataURL();
    document.getElementById("canvasimg").src = dataURL;
    document.getElementById("canvasimg").style.display = "inline";
}
