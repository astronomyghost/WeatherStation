var displayValue = document.getElementById("TestInfo"); 
var test = JSON.parse(post)
for(var i = 0; i < test.length; i++){
	txt = document.createTextNode(test[i]);
	displayValue.appendChild(txt);
}