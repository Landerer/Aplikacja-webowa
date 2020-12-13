$(document).ready(function () {
    var canvas = document.getElementById('canvas');
    var image_id = null;
    // load an undescribed image
    function loadNewImage() {
        canvas.innerHTML = 'Loading new image...';
        $.ajax({
            type: 'GET',
            url: 'images',
            accepts: 'application/json',
        }).done(function (images) {
            console.log(images);
            var new_image_id = images[0].id;
            for (var imageNumber in images) {
                var image = images[imageNumber];
                if (image.id > image_id) {
                    new_image_id = image.id;
                    break;
                }
            }
            image_id = new_image_id;
            console.log('New image ID=' + image_id)
            var image = document.createElement('img');
            image.src = 'image?id=' + image_id;

            canvas.innerHTML = '';
            canvas.appendChild(image);
        })
    }
    loadNewImage();

    var rectCoords = {
        x: 0,
        y: 0,
        startX: 0,
        startY: 0,
        setPosition: function (e) {
            var ev = e || window.event; //Moz || IE
            if (ev.pageX) { //Moz
                this.x = ev.pageX + window.pageXOffset;
                this.y = ev.pageY + window.pageYOffset;
            } else if (ev.clientX) { //IE
                this.x = ev.clientX + document.body.scrollLeft;
                this.y = ev.clientY + document.body.scrollTop;
            }
        },
        fixStartPosition: function () {
            this.startX = this.x;
            this.startY = this.y;
        },
        left: function () { return Math.min(this.x, this.startX); },
        top: function () { return Math.min(this.y, this.startY); },
        width: function () { return Math.abs(this.x - this.startX); },
        height: function () { return Math.abs(this.y - this.startY); },
    };

    var rectangle = null;
    canvas.onmousemove = function (e) {
        rectCoords.setPosition(e);
        if (rectangle !== null) {
            rectangle.style.left = rectCoords.left() + 'px';
            rectangle.style.top = rectCoords.top() + 'px';
            rectangle.style.width = rectCoords.width() + 'px';
            rectangle.style.height = rectCoords.height() + 'px';
        }
    }

    canvas.onclick = function () {
        if (rectangle !== null) {
            var ready_rectangle = rectangle;
            $.ajax({
                type: 'POST',
                url: 'images/' + image_id + '/descriptions/' + rectangle.id,
                accepts: 'application/json',
                dataType: 'json',
                data: {
                    'x': rectCoords.left(),
                    'y': rectCoords.top(),
                    'width': rectCoords.width(),
                    'height': rectCoords.height(),
                }
            }).done(function (data) {
                ready_rectangle.className += ' rectangle_ready';
            })
            rectangle = null;
            canvas.style.cursor = "default";
        } else {
            var descr_id = canvas.childElementCount - 1;
            rectCoords.fixStartPosition();

            rectangle = document.createElement('div');
            rectangle.id = descr_id;
            rectangle.className = 'rectangle'
            rectangle.style.left = rectCoords.left() + 'px';
            rectangle.style.top = rectCoords.top() + 'px';

            canvas.appendChild(rectangle)
            canvas.style.cursor = "crosshair";
        }
    }

    document.getElementById('clear').onclick = function () {
        var confirmation = confirm("Czy na pewno chcesz usunąć wszystkie opisy obrazu?");
        if (confirmation) {
            $.ajax({
                type: 'DELETE',
                url: 'images/' + image_id + '/descriptions',
                accepts: 'application/json',
            }).done(function (data) {
                var child = canvas.firstChild;
                while (child !== null) {
                    var nextSibling = child.nextSibling;
                    if (child.tagName === 'DIV')
                        child.remove();
                    child = nextSibling;
                }
            })
        }
    }

    document.getElementById('undo').onclick = function () {
        var last_child = canvas.childNodes[canvas.childNodes.length - 1];
        console.log(last_child);
        if (last_child.tagName === 'DIV') {
            $.ajax({
                type: 'DELETE',
                url: 'images/' + image_id + '/descriptions/' + last_child.id,
                accepts: 'application/json',
            }).done(function (data) {
                last_child.remove();
            })
        }
    }

    document.getElementById('save').onclick = function () {
        $.ajax({
            type: 'PUT',
            url: 'images/' + image_id,
            accepts: 'application/json',
        }).done(function (data) {
            loadNewImage();
        })

    }

    document.getElementById('next').onclick = function () {
        loadNewImage();
    }

})
