$(document).ready(() => {
    $("#generate_txt").on('click', function () {
        textGen() ;
    })

    function findSeat (input ) {
        const regex = new RegExp(`^${input}$`, 'i'); // ^$ for exact match, 'i' for case-insensitive
        const foundDiv = Array.from(document.querySelectorAll("div.available"))
        .find(div => regex.test(div.innerText.trim()));
        if (foundDiv) {
            console.log("Found ID:", foundDiv.id);
        } else {
            console.log("No match found");
        }
    }

    function textGen () {
        let input = $("input[name='message']").val();
        let initState = $("input[name='init_state']").val()
        let uniqueId = $("input[name='uniqueId']").val()
        let selectedSeatId = $("input[name='selectedSeatId']").val()
        let selectedSeatNo = $("input[name='selectedSeatNo']").val()
        let perviousInput = $("input[name='perviousInput']").val()
        let travelDate = $("input[name='travelDate']").val()
        let boardingPoint = $("input[name='boardingPoint']").val()
        let droppingPoint = $("input[name='droppingPoint']").val()
        $('.material-icons').addClass('d-none');
        $('.spinner-border').removeClass('d-none');
        if (input) {
            generateInterFace(input , 'sender' , formatTime() );
            findSeat(input) ;
            $("input[name='message']").val('');
            $("input[name='selectedSeatNo]").val('') ;
            $("input[name='selectedSeatId]").val('') ;
            // $("input[name='perviousInput]").val('') ;
            $.ajax({
                url: 'http://localhost:8080/get',
                method: 'post',
                contentType: "application/json", 
                data: JSON.stringify({ msg: input  , initState  , avaliable_seats : getAvaliableSeats() , uniqueId , selectedSeatId , selectedSeatNo , perviousInput , travelDate , boardingPoint , droppingPoint}),
                success: (res) => {
                    generateInterFace(res.answer , 'receiver' , formatTime())
                    if( res.info ) generateInterFace(res.info , 'receiver' , formatTime())
                    $("input[name='init_state']").val(res.init_state)
                    $("input[name='uniqueId']").val(res.uniqueId)
                    $("input[name='selectedSeatId']").val(res.selectedSeatId)
                    $("input[name='selectedSeatNo']").val(res.selectedSeatNo)
                    $("input[name='perviousInput']").val(res.perviousInput)
                    $("input[name='travelDate']").val(res.travelDate)
                    $('.spinner-border').addClass('d-none');
                    $('.material-icons').
                    removeClass('d-none');
                },
                error: (err) => {
                    console.error(err)
                }
            })
        }
    }

    function generateInterFace (message , type  , time) {
        let senderInter =
        `
            <div class="message-content ${type}">
                <label for="">${time}</label>
                <div class="msg-block">
                    <p>
                        <pre>${message}</pre>
                    </p>
                </div>
            </div>
        ` ;
        $('.chat-body').append(senderInter);
        focusLastMessage()
    }   

    function getAvaliableSeats() {
        let availableSeats = {};

        $(".available").each(function () {
            const seatText = $(this).text().trim();
            const seatId = this.id; // or $(this).attr("id")
            availableSeats[seatText] = seatId;
        });

        return availableSeats;
    }

    $("input[name='message']").keypress(function (event) {
        if (event.which === 13) {
            event.preventDefault();
            textGen() ;
        }
    });

    function formatTime() {
        let now = new Date();
        let hours = now.getHours();
        let minutes = now.getMinutes();
        let ampm = hours >= 12 ? "PM" : "AM";
    
        // Convert to 12-hour format
        hours = hours % 12 || 12;
        
        // Add leading zero to minutes if needed
        minutes = minutes < 10 ? "0" + minutes : minutes;
    
        // Get yesterday's date
        let yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
    
        // Format the time string
        return `${hours}:${minutes} ${ampm}, Today`;
    }

    function focusLastMessage() {
        let chatBody = $(".chat-body");
        let lastMessage = chatBody.children().last();
    
        if (lastMessage.length) {
            chatBody.animate({
                scrollTop: chatBody.prop("scrollHeight")
            }, 300); // Smooth scrolling effect
        }
    }            
})